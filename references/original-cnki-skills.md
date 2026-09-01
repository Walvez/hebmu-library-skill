# Source Project Notes

This Codex skill was adapted from:

```text
https://github.com/cookjohn/cnki-skills
```

Observed source structure:

```text
skills/cnki-search
skills/cnki-advanced-search
skills/cnki-parse-results
skills/cnki-navigate-pages
skills/cnki-paper-detail
skills/cnki-journal-search
skills/cnki-journal-index
skills/cnki-journal-toc
skills/cnki-download
skills/cnki-export
agents/cnki-researcher.md
```

The original project targets Claude Code and Chrome DevTools MCP. It uses browser JavaScript evaluation to operate CNKI pages, parse search results, inspect journal pages, and export metadata to Zotero.

Codex adaptation decisions:

- Consolidate the original multiple Claude skills into one Codex skill named `cnki-skills`.
- Keep the workflow ideas: CNKI search, advanced search, result parsing, pagination, paper detail extraction, journal workflows, PDF/CAJ download triggering, CNKI export, Zotero import, and verified/unverified reference separation.
- Preserve the upstream task instructions under `references/upstream/` so Codex can read the closest Claude Code recipe for each operation and translate it to available Codex browser/Chrome tools.
- Do not depend on Claude slash commands or `mcp__chrome-devtools__*` tool names.
- Use the user's active Chrome/CNKI session when download access matters.
- Support Zotero metadata import and local PDF/CAJ attachment import after the user has downloaded the files.

License note: the upstream README states MIT license. Preserve attribution when reusing code or workflow text.
