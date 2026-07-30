# Release checklist

1. Update `RELEASE_NOTES.md`.
2. Run `uv run python scripts/bump_version.py X.Y.Z`.
3. Run `./scripts/check.sh`.
4. Run `./scripts/check_artifacts.sh` to build and smoke-test the wheel and source
   distribution in a clean environment.
5. Review and commit all version metadata together.
6. Tag the reviewed commit after it is merged.

Use `uv run python scripts/bump_version.py --check` to verify that all committed
version locations agree without changing files.
