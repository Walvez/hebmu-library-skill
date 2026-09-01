#!/usr/bin/env python3
"""Push CNKI-style metadata and local attachments to Zotero.

This script writes Zotero items through the local Connector API. If an input
record includes ``attachmentPath``, the local file is uploaded as an attachment
after the item metadata is saved.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

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


def make_session_id(items: list[dict[str, Any]]) -> str:
    """Create a deterministic session id so repeated imports are idempotent."""
    key = "|".join(sorted(str(item.get("title", "")) for item in items))
    return hashlib.md5(key.encode("utf-8", errors="surrogateescape")).hexdigest()[:12]


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
    print(f"文库: {data.get('libraryName', '?')}")
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
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_collections()
        return

    status, _ = zotero_request("ping")
    if status == 0:
        print("Error: Zotero 未运行。请启动 Zotero 桌面端。")
        raise SystemExit(1)

    records = load_records(sys.argv[1] if len(sys.argv) > 1 else None)
    items = [build_zotero_item(record) for record in records if record.get("title")]
    if not items:
        print("Error: 无有效论文题名，未写入 Zotero。")
        raise SystemExit(1)

    session_id = make_session_id(items)
    for index, item in enumerate(items):
        item["id"] = f"cnki_{session_id}_{index}"

    payload = {"sessionID": session_id, "uri": items[0].get("url", ""), "items": items}
    status, resp = zotero_request("saveItems", payload)

    if status in {201, 409}:
        if status == 201:
            print(f"成功: 已写入 Zotero 元数据 ({len(items)} 篇)")
        else:
            print(f"已存在: 这批元数据本次 Zotero 会话中已保存过 (session: {session_id})")

        for item in items:
            print(f"  - {item.get('title', '?')}")

        for index, record in enumerate(records):
            attachment_path = record.get("attachmentPath") or record.get("attachment_path")
            if not attachment_path:
                continue
            title = record.get("attachmentTitle") or Path(attachment_path).name
            att_status, att_resp = save_attachment(
                session_id=session_id,
                item_id=items[index]["id"],
                attachment_path=attachment_path,
                title=title,
            )
            if att_status == 201:
                print(f"  附件已添加: {attachment_path}")
            else:
                print(f"  附件添加失败: HTTP {att_status}: {att_resp}")
    elif status == 0:
        print("失败: Zotero 未运行或连接被拒绝")
        raise SystemExit(1)
    else:
        print(f"失败: Zotero 返回 HTTP {status}: {resp}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
