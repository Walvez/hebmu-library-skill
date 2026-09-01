# CNKI Workflow Reference

## Search Plan Template

```markdown
## CNKI 检索计划

- 研究问题：
- 中文关键词：
- 英文关键词：
- 同义词/近义词：
- 建议检索字段：
- 时间范围：
- 文献类型：
- 来源类别：
- 纳入标准：
- 排除标准：
- 核验方式：
```

## Result Record Template

```json
{
  "title": "",
  "authors": [],
  "journal": "",
  "year": "",
  "volume": "",
  "issue": "",
  "pages": "",
  "keywords": [],
  "abstract": "",
  "doi": "",
  "cnki_url": "",
  "database": "",
  "verified": false,
  "verification_source": "",
  "notes": ""
}
```

## Zotero Metadata JSON

Use this minimal shape for `scripts/push_to_zotero.py`:

```json
[
  {
    "title": "论文题名",
    "authors": ["作者一", "作者二"],
    "journal": "期刊名称",
    "year": "2024",
    "pubTime": "2024",
    "keywords": ["关键词一", "关键词二"],
    "abstract": "摘要",
    "link": "https://kns.cnki.net/..."
  }
]
```

With a local PDF/CAJ attachment:

```json
[
  {
    "title": "论文题名",
    "authors": ["作者一", "作者二"],
    "journal": "期刊名称",
    "year": "2024",
    "link": "https://kns.cnki.net/...",
    "attachmentPath": "/Users/name/Downloads/paper.pdf"
  }
]
```

## Download Workflow

Use the upstream `cnki-download.md` recipe for selectors and page behavior.

Operational sequence:

1. Use the user's logged-in Chrome session.
2. Navigate to the paper detail page or inspect the current CNKI detail page.
3. Detect visible captcha or not-logged-in states.
4. If login/captcha is required, pause for the user to complete it in Chrome, then continue.
5. Trigger the visible PDF or CAJ download button.
6. Confirm the downloaded file location before adding it to Zotero as an attachment.

## Project Reference Tables

For `verified_references.csv`, use:

```csv
reference_id,citation,pmid,doi,verification_source,verification_date,notes
```

For `unverified_references.csv`, use:

```csv
reference_id,citation,claimed_pmid,claimed_doi,reason_unverified,notes
```

## Compliance Checklist

- The user is using their chosen CNKI/library/VPN route.
- Login/captcha states are detected and paused for browser-side completion.
- Downloads are triggered from the user's active browser session.
- Batch scope is user-confirmed before processing.
- Metadata is verified before manuscript use.
- Unverified references remain marked unverified.
