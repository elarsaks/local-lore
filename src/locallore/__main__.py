from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from .config import Settings
from .doctor import DoctorError, run_doctor
from .indexing import update_index
from .mcp_server import run_http_server
from .status import get_status


def index(settings: Settings) -> None:
    result, embedded = update_index(settings)
    print(
        f"Indexed {result.messages_added} messages "
        f"from {result.files_changed} changed files; "
        f"embedded {embedded} messages",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="locallore")
    parser.add_argument("command", choices=("serve", "index", "doctor"))
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        settings = Settings.from_env()
        if args.command == "serve":
            run_http_server(settings)
        elif args.command == "index":
            index(settings)
        elif args.command == "doctor":
            report = run_doctor(settings)
            for check in report.checks:
                print(f"ok: {check}", file=sys.stderr)
            status = get_status(settings.database_path)
            print(
                f"LocalLore ready (schema version {status['schema_version']})",
                file=sys.stderr,
            )
    except (DoctorError, OSError, sqlite3.Error, ValueError) as exc:
        logging.getLogger(__name__).error("LocalLore startup failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
