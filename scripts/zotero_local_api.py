#!/usr/bin/env python3
"""Zotero Desktop 本地 API 写链路(v2 修复版,实测 107 篇)。

用法:
  python3 zotero_local_api.py import <records.json> <collectionKey> [--mode en|zh]

records.json 格式: [{"no": "21", "title": "...", "authors": ["张三", "李四"],
                    "journal": "...", "year": "2019", "file": "/abs/path.pdf"}]
  - no        -> 写入 extra "筛选清单No: <no>",用于幂等(重跑跳过已导入)
  - authors   -> 全中文名用单字段;含空格拆 first/last
  - file      -> 可缺省(只建条目不挂附件)

幂等:导入前 GET 全部 journalArticle,按 extra 里的 筛选清单No 建已导入集合。
注意:本地 API 忽略 collection= 查询参数,幂等检查只看 extra。

坑(已修,勿回退):
  - 文件认证 POST 需要 If-None-Match: *(新文件)或 If-Match: <version>(已存在)
  - 上传是顶级路径 /api/local/uploads/<uploadKey>,不是 /api/users/0/local/uploads
  - DELETE 条目用 If-Unmodified-Since-Version,不是 If-Match
  - 授权头必须同时带 Zotero-Server-ID 与 Authorization
"""
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOCAL = "http://127.0.0.1:23119"
API = LOCAL + "/api/users/0"
SERVER_ID = "Q2EDu0aTnedN"          # Zotero Settings -> Advanced -> Server ID
API_KEY = "4pzFIbGFoxWUjzt21Vr24fB53aCZc2UB"  # /api/local/authorize 签发,过期则重签
HDRS = {"Zotero-Server-ID": SERVER_ID, "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"}


def call(method, path, data=None, raw=None, ctype=None, extra=None):
    h = dict(HDRS)
    if extra:
        h.update(extra)
    body = json.dumps(data).encode() if data is not None else (raw if raw is not None else None)
    if ctype:
        h["Content-Type"] = ctype
    req = urllib.request.Request(f"{API}{path}", data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        txt = resp.read().decode()
        st = resp.status
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        st = e.code
    try:
        return st, json.loads(txt)
    except Exception:
        return st, txt


def item_json(rec, coll):
    creators = []
    for a in rec.get("authors") or []:
        if " " in a:
            last, first = a.rsplit(" ", 1)
            creators.append({"creatorType": "author", "firstName": first, "lastName": last})
        else:
            creators.append({"creatorType": "author", "name": a})
    return {
        "itemType": "journalArticle",
        "title": rec["title"],
        "creators": creators,
        "publicationTitle": rec.get("journal", ""),
        "date": str(rec.get("year", "")),
        "language": "zh" if re.search(r"[\u4e00-\u9fff]", rec["title"]) else "en",
        "extra": f"筛选清单No: {rec['no']}",
        "collections": [coll],
        "tags": [],
    }


def attach(att_key, pdf_path):
    p = Path(pdf_path)
    md5 = hashlib.md5(p.read_bytes()).hexdigest()
    fname = p.name
    form = (f"md5={md5}&filename={urllib.parse.quote(fname)}&filesize={p.stat().st_size}"
            f"&mtime={int(p.stat().st_mtime * 1000)}")
    h = dict(HDRS)
    h["If-None-Match"] = "*"
    h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(f"{API}/items/{att_key}/file", data=form.encode(), headers=h, method="POST")
    resp = urllib.request.urlopen(req, timeout=60)
    txt = resp.read().decode()
    if resp.status != 200 or "uploadKey" not in txt:
        return f"auth HTTP {resp.status}: {txt[:120]}"
    uk = json.loads(txt)["uploadKey"]
    up = urllib.request.Request(f"{LOCAL}/api/local/uploads/{uk}", data=p.read_bytes(),
                                headers={"Content-Type": "application/pdf"}, method="POST")
    st = urllib.request.urlopen(up, timeout=120).status
    if st != 201:
        return f"upload HTTP {st}"
    st, _ = call("POST", f"/items/{att_key}/file", raw=(
        f"upload={uk}&{form}").encode(), ctype="application/x-www-form-urlencoded")
    if st != 204:
        return f"register HTTP {st}"
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    if sys.argv[1] == "import":
        records = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        coll = sys.argv[3]
        st, items = call("GET", "/items?itemType=journalArticle&limit=100&format=json")
        have = {m.group(1) for it in items if isinstance(it, dict)
                and (m := re.search(r"筛选清单No:\s*(\d+)", it["data"].get("extra", "")))}
        ok = fail = skip = 0
        for rec in records:
            if rec["no"] in have:
                skip += 1
                continue
            st2, resp = call("POST", "/items", data=[item_json(rec, coll)])
            if st2 != 200:
                print(f"create fail {rec['no']}: {st2}")
                fail += 1
                continue
            key = resp["successful"]["0"]["key"]
            if rec.get("file") and Path(rec["file"]).exists():
                st3, att = call("POST", "/items", data=[{
                    "itemType": "imported_file", "linkMode": "imported_file",
                    "parentItem": key, "filename": Path(rec["file"]).name,
                    "collections": [coll], "tags": []}])
                if st3 != 200:
                    print(f"att create fail {rec['no']}: {st3}")
                    fail += 1
                    continue
                akey = att["successful"]["0"]["key"]
                err = attach(akey, rec["file"])
                if err:
                    print(f"attach fail {rec['no']}: {err}")
                    fail += 1
                    continue
            ok += 1
            time.sleep(0.2)
        print(f"DOImport ok={ok} fail={fail} skip={skip}")


if __name__ == "__main__":
    main()
