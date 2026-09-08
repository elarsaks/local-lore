---
description: Search earlier Claude Code sessions by meaning, keyword, project, date, role, or file with LocalLore.
---

# Search session history

Use `locallore_search` when you remember a concept, phrase, project, time
period, role, or touched file from an earlier session.

## Search broadly

Start with the idea you want to recover:

```text
Use LocalLore to find why we chose a read-only container filesystem.
```

The query runs through keyword and semantic retrieval. Results are
deduplicated by normalized text and limited to 8 by default (maximum 25).

## Narrow the result set

The MCP tool accepts optional filters:

| Filter | Meaning | Example |
| --- | --- | --- |
| `project` | Exact indexed project name | `local-lore` |
| `after` | Timestamp at or after this value | `2026-01-01T00:00:00Z` |
| `before` | Timestamp before this value | `2026-02-01T00:00:00Z` |
| `role` | `user`, `assistant`, or `tool` | `assistant` |
| `files` | Messages associated with every supplied path | `src/locallore/search.py` |
| `limit` | Number of results, clamped to 1–25 | `12` |

For example:

```text
Search LocalLore for "ranking" in project local-lore, after 2026-01-01,
limited to messages associated with src/locallore/search.py.
```

## Retrieve nearby messages

Search results are excerpts rather than full transcripts. Pass a result's
`session_id` and `message_id` to `locallore_context`. Set `before` and `after`
between 0 and 10 to control the context window.

```text
Get five messages before and two after this LocalLore result.
```

This two-step pattern keeps retrieval small: search first, then expand only the
relevant result.
