# Release checklist

The repository is intentionally frozen on Python 3.12.13, uv 0.11.6, exact
Python requirements, immutable container digests, and commit-pinned GitHub
Actions. Do not refresh these inputs unless intentionally creating a new
maintained release.

1. Update `RELEASE_NOTES.md`.
2. Run `uv run python scripts/bump_version.py X.Y.Z`.
3. Run `./scripts/check.sh`.
4. Review and commit all version metadata together.
5. Tag the reviewed commit after it is merged.

Use `uv run python scripts/bump_version.py --check` to verify that all committed
version locations agree without changing files.
