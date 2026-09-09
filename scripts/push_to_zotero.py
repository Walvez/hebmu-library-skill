#!/usr/bin/env python3
"""Push CNKI-style metadata and local attachments to Zotero.

This script writes Zotero items through the local Connector API. If an input
record includes ``attachmentPath``, the local file is uploaded as an attachment
after the item metadata is saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any




ZOTERO_API = "http://127.0.0.1:23119/connector"
HTTP_TIMEOUT = 15


def zotero_request(endpoint: str, data: dict[str, Any] | None = None) -> tuple[int, Any]:
    """Send a JSON request to Zotero local Connector API."""
    body = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{ZOTERO_API}/{endpoint}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Zotero-Connector-API-Version": "3",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
        text = resp.read().decode("utf-8")
        return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text) if text else None
        except json.JSONDecodeError:
            return exc.code, {"error": text}
    except urllib.error.URLError:
        return 0, None
    except TimeoutError:
        return -1, {"error": f"request timed out after {HTTP_TIMEOUT}s"}


def make_session_id(items, target, library_id):
    """Bind content and input order to the destination; omit volatile transport fields."""
    canonical = [{k: v for k, v in item.items() if k not in ('id', 'accessDate')}
                 for item in items]
    key = json.dumps([library_id, target, canonical], ensure_ascii=False,
                     sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]


def check_target(target, library_id):
    """Read-only check; cannot atomically lock Connector's selected UI target."""
    if (not isinstance(target, str) or not re.fullmatch(r'[CL][1-9][0-9]*', target)
            or type(library_id) is not int or library_id < 1):
        return False
    selected = get_selected_collection()
    if not isinstance(selected, dict):
        return False
    current = ('C' + str(selected['id']) if selected.get('id') is not None
               else 'L' + str(selected.get('libraryID')))
    return (current == target and selected.get('libraryID') == library_id
            and selected.get('libraryEditable') is True
            and selected.get('editable') is True)


def get_selected_collection() -> dict[str, Any] | None:
    """Return Zotero's currently selected collection metadata."""
    status, data = zotero_request("getSelectedCollection")
    if status != 200 or not data:
        return None
    return data


def list_collections() -> None:
    """Print the currently selected Zotero collection and available targets."""
    data = get_selected_collection()
    if not data:
        print("Error: 无法连接 Zotero。请确保 Zotero 桌面端已启动。")
        raise SystemExit(1)

    print(f"当前选中分类: {data.get('name', '?')} (ID: {data.get('id', '?')})")
    print(f"文库: {data.get('libraryName', '?')} (libraryID: {data.get('libraryID', '?')})")
    print()
    print("可用分类:")
    for target in data.get("targets", []):
        indent = "  " * int(target.get("level", 0))
        recent = " *" if target.get("recent") else ""
        print(f"  {indent}{target.get('name', '?')} (ID: {target.get('id', '?')}){recent}")


def parse_elearning(text: str) -> dict[str, Any]:
    """Parse CNKI ELEARNING export text when available."""
    text = text.replace("<br>", "\n").replace("\r", "")
    text = re.sub(r"<[^>]+>", "", text)

    def get(key: str) -> str:
        match = re.search(rf"{re.escape(key)}:\s*(.+?)(?=\n|$)", text)
        return match.group(1).strip() if match else ""

    return {
        "title": get("Title-题名"),
        "authors": [a.strip() for a in get("Author-作者").split(";") if a.strip()],
        "journal": get("Source-刊名"),
        "year": get("Year-年"),
        "pubTime": get("PubTime-出版时间"),
        "keywords": [k.strip() for k in get("Keyword-关键词").split(";") if k.strip()],
        "abstract": get("Summary-摘要"),
        "volume": get("Roll-卷"),
        "issue": get("Period-期"),
        "pages": get("Page-页码"),
        "link": get("Link-链接"),
    }


def normalize_authors(value: Any) -> list[dict[str, str]]:
    """Return Zotero creator objects from list or semicolon-separated text."""
    if isinstance(value, str):
        names = [name.strip() for name in re.split(r"[;；]", value) if name.strip()]
    elif isinstance(value, list):
        names = [str(name).strip() for name in value if str(name).strip()]
    else:
        names = []
    return [{"name": name, "creatorType": "author"} for name in names]


def build_zotero_item(record: dict[str, Any]) -> dict[str, Any]:
    """Build a Zotero journalArticle item from normalized CNKI metadata."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = record.get("link") or record.get("cnki_url") or record.get("url") or ""
    keywords = record.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[;；,，]", keywords) if k.strip()]

    item: dict[str, Any] = {
        "itemType": "journalArticle",
        "title": record.get("title", ""),
        "abstractNote": record.get("abstract", ""),
        "date": record.get("pubTime") or record.get("year", ""),
        "language": "zh-CN",
        "libraryCatalog": "CNKI",
        "accessDate": now,
        "volume": record.get("volume", ""),
        "issue": record.get("issue", ""),
        "pages": record.get("pages", ""),
        "publicationTitle": record.get("journal", ""),
        "url": url,
        "creators": normalize_authors(record.get("authors", [])),
        "tags": [{"tag": k, "type": 1} for k in keywords],
        "attachments": [],
    }

    extra_parts = []
    for source_key, extra_key in [
        ("doi", "DOI"),
        ("database", "database"),
        ("cnki_url", "CNKI"),
        ("verification_source", "verification_source"),
    ]:
        if record.get(source_key):
            extra_parts.append(f"{extra_key}: {record[source_key]}")
    if extra_parts:
        item["extra"] = "\n".join(extra_parts)

    return item


def save_attachment(
    session_id: str,
    item_id: str,
    attachment_path: str,
    title: str = "Full Text",
) -> tuple[int, Any]:
    """Upload a local PDF/CAJ file to Zotero as an attachment."""
    path = Path(attachment_path).expanduser()
    if not path.exists() or not path.is_file():
        return 0, f"attachment file not found: {path}"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        content_type = "application/pdf"
    elif suffix == ".caj":
        content_type = "application/octet-stream"
    else:
        content_type = "application/octet-stream"

    metadata = json.dumps(
        {
            "id": f"{item_id}_attachment",
            "parentItemID": item_id,
            "title": title or path.name,
            "filename": path.name,
            "contentType": content_type,
        },
        ensure_ascii=True,
    )

    req = urllib.request.Request(
        f"{ZOTERO_API}/saveAttachment?sessionID={session_id}",
        data=path.read_bytes(),
        headers={
            "Content-Type": content_type,
            "X-Metadata": metadata,
            "X-Zotero-Connector-API-Version": "3",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.status, None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - surface Zotero/IO failures clearly
        return 0, str(exc)


def load_records(path_arg: str | None) -> list[dict[str, Any]]:
    """Load a single record or record list from a JSON file or stdin."""
    if path_arg:
        data = json.loads(Path(path_arg).read_text(encoding="utf-8"))
    else:
        data = json.load(sys.stdin)

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and "ELEARNING" in data:
        parsed = parse_elearning(data["ELEARNING"])
        parsed.update({k: v for k, v in data.items() if k != "ELEARNING"})
        records = [parsed]
    elif isinstance(data, dict):
        records = [data]
    else:
        raise ValueError("Input must be a JSON object or array")

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--target', help='Confirmed local Connector tree ID: C123 or L1')
    parser.add_argument('--library-id', type=int)
    args = parser.parse_args()
    if args.list:
        list_collections()
        return
    if (not args.target or not re.fullmatch(r'[CL][1-9][0-9]*', args.target)
            or not args.library_id or args.library_id < 1):
        parser.error('Import requires --target C123|L1 and --library-id N; no write attempted')
    records = load_records(args.input)
    # Reject the batch before writing: filtering only items misaligns attachment parents.
    if not records or any(not isinstance(r, dict) or not isinstance(r.get('title'), str)
                          or not r['title'].strip() for r in records):
        print('Invalid/untitled record; no metadata or attachment write attempted.')
        raise SystemExit(1)
    items = [build_zotero_item(record) for record in records]
    if not check_target(args.target, args.library_id):
        print('Target missing, mismatched, unreadable or not editable; no write attempted.')
        raise SystemExit(1)
    session_id = make_session_id(items, args.target, args.library_id)
    for index, item in enumerate(items):
        item["id"] = f"cnki_{session_id}_{index}"

    payload = {"sessionID": session_id, "uri": items[0].get("url", ""), "items": items}
    status, resp = zotero_request("saveItems", payload)

    if status == 201:
        if not check_target(args.target, args.library_id):
            print(f'Metadata may have been written; target changed. Reconcile session {session_id}, do not re-import.')
            raise SystemExit(2)
        print(f'Metadata accepted; membership/parent readback required (session: {session_id}, target: {args.target}).')
        failed = False
        for item in items:
            print(f"  - {item.get('title', '?')}")

        for index, record in enumerate(records):
            attachment_path = record.get("attachmentPath") or record.get("attachment_path")
            if not attachment_path:
                continue
            if not check_target(args.target, args.library_id):
                print('Partial: target changed; stop attachments and reconcile metadata.')
                raise SystemExit(2)
            title = record.get("attachmentTitle") or Path(attachment_path).name
            att_status, att_resp = save_attachment(
                session_id=session_id,
                item_id=items[index]["id"],
                attachment_path=attachment_path,
                title=title,
            )
            if att_status == 201:
                print(f"  Attachment request accepted; parent readback required: {attachment_path}")
            else:
                print(f"  附件添加失败: HTTP {att_status}: {att_resp}")
                failed = True
        if failed:
            raise SystemExit(2)
    elif status == 0:
        print("失败: Zotero 未运行或连接被拒绝")
        raise SystemExit(1)
    else:
        print(f"Unverified HTTP {status}; session {session_id}. Stop; reconcile before retry or attachments.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
