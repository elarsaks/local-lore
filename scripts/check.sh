#!/bin/sh
set -eu

cd -- "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"

uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv run --locked mypy src/locallore
shellcheck -x -P scripts scripts/*.sh
uv run --locked pytest -q \
  --cov=locallore \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml
