from __future__ import annotations

import argparse
import sys

from .mcp_server import run_server
from .status import get_status


def main() -> None:
    parser = argparse.ArgumentParser(prog="locallore")
    parser.add_argument("command", choices=("mcp", "index", "doctor"))
    args = parser.parse_args()

    if args.command == "mcp":
        run_server()
    elif args.command == "index":
        print("Milestone 1: no index is configured yet", file=sys.stderr)
    else:
        status = get_status()
        print(f"LocalLore ready (schema version {status['schema_version']})", file=sys.stderr)


if __name__ == "__main__":
    main()
