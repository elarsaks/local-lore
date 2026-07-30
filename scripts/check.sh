#!/bin/sh
set -eu

cd -- "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"

uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked mypy src/locallore
uv run --locked python scripts/bump_version.py --check
shellcheck -x -P scripts scripts/*.sh
uv run --locked pytest -q \
  --cov=locallore \
  --cov-report=term-missing
