# Retrieve your first memory

This tutorial takes you from a fresh installation to a search result returned
inside Claude Code. You need Docker with Compose v2, Claude Code with plugin
support, and an existing Claude projects directory (normally
`~/.claude/projects`).

## 1. Install the plugin

Run these commands in Claude Code:

```text
/plugin marketplace add elarsaks/local-lore
/plugin install locallore@locallore
/reload-plugins
/locallore:setup
```

Setup builds the pinned container image, starts the persistent daemon, waits
for the initial index, and runs health and security checks. The first build
needs internet access to obtain pinned Python packages and the embedding model.
The complete first setup can take 30 minutes or longer depending on the network,
hardware, Docker build cache, and amount of session history. Keep Docker running
and allow the setup command to finish. Runtime inference is local-only.

## 2. Check the index

Ask Claude to use `locallore_status`. A ready installation reports an idle
refresh state, an indexed message count, and the daemon version.

You can also check the installation from the repository checkout:

```bash
./scripts/status.sh
./scripts/doctor.sh
```

## 3. Search by meaning

In a new Claude Code session, ask:

```text
Search LocalLore for the session where we decided how to handle database migrations.
```

Claude calls `locallore_search`. LocalLore combines exact-term matches with
semantic similarity, so the result can still be useful when your wording
differs from the original conversation.

Each result includes a session ID, message ID, project, role, timestamp,
excerpt, score, and any detected file paths.

## 4. Expand the context

Ask Claude to show the messages around the best result. It calls
`locallore_context` with the result's session and message IDs. The default
window returns up to three messages before and after the selected message.

You have now used the complete retrieval path: a natural-language request,
hybrid search, a ranked excerpt, and bounded surrounding context.

## Next steps

- [Narrow searches with filters](../how-to/search-session-history.md).
- [Understand how the components fit together](../explanation/architecture.md).
- [Troubleshoot an unhealthy daemon](../how-to/troubleshoot.md).
