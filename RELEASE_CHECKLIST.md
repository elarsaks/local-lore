# LocalLore 0.1 Release Checklist

Complete every item before publishing version 0.1. Record links to the relevant
pull request, CI run, or release artifact next to each item as it is completed.

## Repository and release metadata

- [x] Add the MIT project license and declare it in the package metadata.
- [x] Confirm version `0.1.0` agrees in `pyproject.toml`,
  `.claude-plugin/plugin.json`, and `src/locallore/__init__.py`.
- [x] Add [release notes](RELEASE_NOTES.md) covering user-visible behavior,
  installation requirements, privacy limitations, and known issues.
- [x] Confirm the [README](README.md) installation, upgrade, troubleshooting,
  and data deletion instructions match the release candidate.
- [x] Confirm the release-candidate source contains only synthetic session
  fixtures and no generated database, model cache, credentials, or other
  private data. Recheck the final artifact before publishing it.

## Automated verification

- [ ] Run the complete test suite with `uv run pytest` from a clean checkout.
- [ ] Expand CI to run the complete test suite. The current workflow runs only
  selected test files outside the Docker image checks.
- [ ] Confirm `uv sync --locked --dev` succeeds with Python 3.12 from a clean
  environment and that `uv.lock` contains all release dependencies.
- [ ] Build the release image from scratch with `./scripts/build.sh`.
- [ ] Run `./scripts/doctor.sh` successfully against a representative local
  Claude projects directory.
- [ ] Verify indexing, embedding inference, keyword search, semantic search,
  and MCP startup with Docker networking disabled.
- [ ] Verify the session-history mount is read-only, the container filesystem
  is read-only, and indexed data persists across ephemeral containers.
- [ ] Review the performance test results and document any accepted regression
  in search latency or peak memory use.

## Manual acceptance

- [ ] Validate the plugin with the current stable Claude Code release.
- [ ] On a clean machine with only the documented prerequisites, install from
  the release candidate, build once online, and then start the plugin offline.
- [ ] Confirm `/mcp` reports `locallore` as connected and exposes only
  `locallore_status`, `locallore_search`, and `locallore_context`.
- [ ] Ask representative `/remember` questions and confirm results include
  useful evidence, timestamps, projects, and file paths without exposing
  unbounded message content.
- [ ] Confirm malformed and incomplete JSONL records are handled as documented
  without corrupting checkpoints or preventing other sessions from indexing.
- [ ] Confirm an unchanged history refresh is idempotent and that appended,
  replaced, and truncated session files are refreshed correctly.
- [ ] Test upgrade from the previous supported build while retaining the
  existing Docker volume.
- [ ] Test the documented indexed-data deletion procedure and confirm source
  Claude session files remain untouched.

## Security and privacy review

- [ ] Confirm runtime has no network interface, telemetry, remote inference
  fallback, or model download path.
- [ ] Confirm the container runs as the documented unprivileged user with all
  capabilities dropped and privilege escalation disabled.
- [ ] Confirm MCP inputs and outputs are bounded, SQL values are parameterized,
  and arbitrary SQL is not exposed.
- [ ] Inspect logs and errors to ensure private message content is not emitted
  and stdout remains reserved for MCP protocol messages.
- [ ] Re-read the README privacy warning and confirm it clearly states that the
  Docker volume contains plaintext copies and embeddings of session content.

## Publish

- [ ] Ensure all required CI checks pass on the exact release commit.
- [ ] Create and push the signed version tag for the final version.
- [ ] Publish the release notes and any installation artifact from that tag.
- [ ] Install once from the published source or artifact and repeat the MCP
  connection and `/remember` smoke tests.
