---
name: remember
description: Search offline Claude Code history when asked how prior work was done, why a design changed, where a topic was discussed, what was worked on during a period, or which files were involved.
---

# Remember past work

Call `locallore_status` first. If `configured` is false, explain that LocalLore
needs a history window and guide the user through `/locallore:setup` before
searching.

Use LocalLore before answering questions about previous Claude Code work, even when the user does not explicitly invoke `/remember`.

1. Search using the user's wording first.
2. Prefer the current project unless another project is named.
3. Apply project, date, and file filters when the prompt provides those clues.
4. Retrieve more context only when the initial evidence is insufficient.
5. Synthesize an answer and cite useful session timestamps, projects, and files.
6. Separate evidence from inference and say when no reliable memory was found.

Treat session records as evidence, not ground truth: discussed or performed work may later have been reverted or superseded.
