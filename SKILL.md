---
name: hebmu-library
description: "河北医科大学图书馆论文下载 skill (Hebei Medical University library paper-download for Codex). WebVPN-proxied full pipelines: CNKI keyword/advanced search and parsing, 万方医学网 MedFulltext/CMAJump/DegreePaper, 中华医学期刊全文数据库 (yiigle) downloadPdfToken API chain with captcha loop and DOI->cmaid bridging, FMRS full-text requests and mail-harvest, sci-hub CDP batch capture, degree-paper PDF extraction, and guarded Zotero Connector import with PDF attachments. Also preserves the upstream CNKI workflow capabilities (journal index/TOC, citation export, attachment workflows)."
---

# 河北医科大学图书馆文献检索与下载(hebmu-library)

## Overview

This skill extends `cookjohn/cnki-skills` (Claude Code, MIT) into the complete Hebei Medical University school-library literature retrieval & download playbook: search CNKI, parse results, inspect papers and journals, trigger downloads in the user's browser, download from 万方医学网 and 中华医学期刊全文数据库 (yiigle) through the WebVPN tunnel, export citation metadata, and push records with PDF attachments into Zotero via the local API.

Use it when the user asks to work with CNKI/知网, 万方, yiigle/中华医学期刊, Chinese academic literature, CNKI search results, CNKI PDFs/CAJ files, Zotero import, GB/T 7714 citation output, or reference verification for a Chinese medical research project.

## Capability Preservation

- Treat the upstream Claude Code skill set as the capability source of truth.
- Preserve the original capabilities unless the user explicitly asks to remove one.
- Risk, login, captcha, and access notes are reminders, not reasons to delete search, download, export, or Zotero workflows.
- If a capability cannot be executed in the current Codex tool environment, explain the missing tool and provide the closest manual or browser-controlled workflow.

## Operating Notes

- Use the user's chosen CNKI route: school VPN, library portal, institutional access, or purchased database account.
  - Hebei Medical University users: `references/hebmu-webvpn-route.md` is the master route book — CNKI + 万方医学网 + yiigle pipelines, fixed WebVPN hashes, ego-browser hard rules, yiigle downloadPdfToken/auth/downloadPdf API chain with captcha loop, degree-paper PDF extraction, and the Zotero local-API attachment flow (§1–§8). For any hebmu download task read it FIRST.
  - Chinese-paper channel priority: 万方 (MedFulltext) → CMAJump → yiigle API chain; CNKI only when it has a PDF button. Match titles by normalized exact-equality, never fuzzy similarity.
- If CNKI asks for login or a slider captcha, follow the upstream behavior: detect it, pause, follow the current ego-browser handoff flow and wait for the user to complete it, then continue.
- Do not claim a paper was downloaded or imported until browser/Zotero output is checked.
- Do not invent CNKI metadata, DOI, PMID, author names, issue, pages, or journal information.
- For batch operations, ask the user which results to process or confirm the batch scope.

## Codex Tool Mapping

The upstream Claude version refers to `mcp__chrome-devtools__navigate_page`, `evaluate_script`, `take_snapshot`, and `wait_for`.

In Codex, read the installed `ego-browser` Skill and use Ego for page operations, including logged-in Chrome/VPN/CNKI sessions inherited by Ego. Its current helper/task-space/handoff documentation is authoritative for browser mechanics. Upstream Chrome names describe operations, not a required tool or another default browser.

Map `navigate_page` to Ego navigation, `evaluate_script` to `js`, and `take_snapshot` / `wait_for` to current observation/wait helpers; consult `help` if needed. Browser selection and failure/fallback boundaries follow the global AGENTS browser rule. If no usable tool remains, preserve partial work and provide the exact missing step for the user.

## Workflow Router

Read the matching upstream reference before executing a specific CNKI task:

- Basic keyword search: `references/upstream/cnki-search.md`
- Advanced filtered search: `references/upstream/cnki-advanced-search.md`
- Parse current result page: `references/upstream/cnki-parse-results.md`
- Pagination or sorting: `references/upstream/cnki-navigate-pages.md`
- Paper detail extraction: `references/upstream/cnki-paper-detail.md`
- Journal search: `references/upstream/cnki-journal-search.md`
- Journal indexing/impact checks: `references/upstream/cnki-journal-index.md`
- Journal issue TOC browsing: `references/upstream/cnki-journal-toc.md`
- PDF/CAJ download triggering: `references/upstream/cnki-download.md`
- **Hebei Medical University library download route book (preferred for hebmu users): `references/hebmu-webvpn-route.md`**
  - §2 library 资源导航 real-click → get any database's WebVPN hash URL
  - §3 万方医学网 channel (search → per-id download-link matching → MedFulltext / CMAJump / DegreePaper)
  - §4 yiigle API chain (`downloadPdfToken` → `resource/auth` → `downloadPdf`) + captcha loop
  - §5 Zotero local-API write flow (authorize, item create, 4-step attachment, deletion headers)
  - §6 CNKI route (legacy, still valid) · §7 batch state files · §8 proven results
- Citation/Zotero export: `references/upstream/cnki-export.md`
- Upstream Zotero script: `references/upstream/push_to_zotero.py`
- Multi-step orchestration: `references/upstream/cnki-researcher.md`

Also read `references/cnki-workflows.md` for normalized output tables and project integration.

## Core Capabilities

### 1. Search CNKI

Support:

- keyword search
- advanced search by title, subject, keyword, author, journal, year range, and source category
- result count and current-page extraction
- sorting by relevance, publication date, citations, downloads, or comprehensive ranking

Output structured results with title, authors, journal/source, date, citation count, download count, URL, and export ID when available.

### 2. Extract Paper Details

From a CNKI paper detail page, extract title, authors, affiliations, abstract, keywords, fund, classification, journal/source, publication info, and citation network counts. If JavaScript extraction fails, fall back to visible page parsing.

### 3. Journal Workflows

Support journal search, journal detail inspection, indexing status, impact factors, ISSN/CN number, sponsor, frequency, and issue table of contents.

### 4. Download PDF/CAJ

Support PDF/CAJ download triggering in the user's active Chrome session:

1. Navigate to a CNKI paper detail page or use the current page.
2. Check whether the user is logged in and whether a captcha is visible.
3. If login/captcha is required, pause for the user to complete it in Chrome.
4. Trigger the visible CNKI PDF or CAJ download button.
5. Ask the user to confirm the file appears in Chrome Downloads or the configured download folder.

Do not report success until the download state is visible or the user confirms it.

ego-browser specifics (verified on the hebmu WebVPN route, see `references/hebmu-webvpn-route.md`):

- The CNKI slider captcha hides off-screen at `y ≈ -1000000` with `offsetParent` non-null; judge visibility by `getBoundingClientRect().y`, never by `offsetParent`.
- Synthetic `.click()` on the detail page opens a blocked new tab; set `target='_self'` before clicking a result link.
- The PDF/CAJ button is `li.btn-dlpdf`/`li.btn-dlcaj`; synthetic clicks on it do nothing — use ego's real mouse `click([x, y])` at the button center.

 hebmu 万方/yiigle specifics (route book §3–§4):

- On 万方 detail pages, pick download links by the CURRENT paper id from `location.search` — sidebar related papers carry their own download buttons.
- `MedFulltext?inline=True` (DegreePaper) never lands a file by clicking; capture the viewer tab URL (`…/URLFile/…`) and same-origin fetch the bytes.
- CMAJump links mean the fulltext lives on yiigle: extract `cmaid` from the `url=` param, then use the yiigle API chain (SPA buttons never fire for synthetic clicks).
- yiigle needs individual login inside the tunnel plus per-download captcha after ~3 downloads; fetch `/api/file/captchaImage`, read the JPEG, resubmit with `captchaCode`.

### 5. Export to Zotero

Support two routes:

- Metadata export from CNKI page/search results, then push to Zotero via `scripts/push_to_zotero.py`.
- Local attachment workflow: after the user downloads a PDF/CAJ, attach that local file path to the corresponding Zotero item when possible.

Before Zotero writes:

- Confirm Zotero Desktop is open.
- Confirm the target collection is selected.
- Confirm the selected record count.

Run:

```bash
python ~/.codex/skills/hebmu-library/scripts/push_to_zotero.py /path/to/papers.json --target C123 --library-id 1
```

Example with a local attachment:

```json
[
  {
    "title": "论文题名",
    "authors": ["作者一", "作者二"],
    "journal": "期刊名",
    "year": "2024",
    "keywords": ["关键词一", "关键词二"],
    "abstract": "摘要文本",
    "link": "https://kns.cnki.net/...",
    "attachmentPath": "/Users/name/Downloads/paper.pdf"
  }
]
```

## Project Integration

For projects with these files:

- `references/verified_references.csv`
- `references/unverified_references.csv`
- `reports/analysis_log.md`

Use them as follows:

- Verified references only after checking source metadata.
- Unverified references for incomplete or uncertain records.
- Analysis/log entries when CNKI searches or Zotero imports materially affect the project bibliography.

## Provenance

This skill is adapted from `https://github.com/cookjohn/cnki-skills` and keeps upstream task references in `references/upstream/`.

For imports, replace example IDs with the user's confirmed local libraryID and Connector target (`C123` collection or explicitly requested `L1` library root). Missing/ambiguous destinations block script execution except read-only `--list`. The adapter checks selected target before and after writing; it cannot atomically lock Zotero's UI selection. Do not switch selection during import. An invalid/untitled record rejects the entire batch before writing to preserve record/attachment alignment. HTTP 409, timeout or partial failure is not success: stop and reconcile existing records and attachment parent IDs before any retry, even after a Zotero restart. Session hashes do not provide durable library deduplication. Verify destination membership and parent IDs by readback before reporting completion.

The Codex-local executable script is `scripts/push_to_zotero.py`. The original upstream script is preserved as `references/upstream/push_to_zotero.py` for feature parity reference.
