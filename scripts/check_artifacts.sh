#!/bin/sh
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
requested_directory=${1:-}
temporary_artifacts=
if [ -z "$requested_directory" ]; then
  temporary_artifacts=$(mktemp -d)
  artifact_directory=$temporary_artifacts/dist
else
  artifact_directory=$ROOT/$requested_directory
fi
smoke_root=$(mktemp -d)

cleanup() {
  rm -rf "$smoke_root"
  if [ -n "$temporary_artifacts" ]; then
    rm -rf "$temporary_artifacts"
  fi
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$artifact_directory"
cd "$ROOT"
uv build --out-dir "$artifact_directory"

set -- "$artifact_directory"/locallore-*.whl
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Expected exactly one LocalLore wheel in $artifact_directory." >&2
  exit 1
fi
wheel=$1

set -- "$artifact_directory"/locallore-*.tar.gz
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Expected exactly one LocalLore source distribution in $artifact_directory." >&2
  exit 1
fi
sdist=$1

python3 - "$sdist" <<'PY'
from pathlib import Path
import sys
import tarfile

sdist = Path(sys.argv[1])
with tarfile.open(sdist) as archive:
    names = archive.getnames()
assert any(
    name.endswith("/src/locallore/storage/schema.sql") for name in names
), "schema.sql"
PY

uv venv --python 3.12 "$smoke_root/venv" >/dev/null
python_path=$smoke_root/venv/bin/python
uv pip install --python "$python_path" "$wheel" >/dev/null

(
  cd "$smoke_root"
  "$python_path" - <<'PY'
from importlib import metadata, resources
from pathlib import Path
import sys

import locallore
from locallore.storage.db import connect, migrate

assert metadata.version("locallore") == locallore.__version__
assert str(Path(locallore.__file__).resolve()).startswith(str(Path(sys.prefix).resolve()))

schema = resources.files("locallore.storage").joinpath("schema.sql")
assert schema.is_file()

connection = connect(Path("artifact-smoke.db"))
migrate(connection)
connection.execute("SELECT count(*) FROM messages_fts").fetchone()
connection.close()
PY
  "$python_path" -m locallore --help >/dev/null
)

echo "ok: wheel and source distribution passed clean-install smoke tests"
