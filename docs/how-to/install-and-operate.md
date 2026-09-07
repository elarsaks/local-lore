# Install and operate LocalLore

## Install from a checkout

Run the installer for both initial setup and later updates:

```bash
./scripts/install.sh
```

To index a non-default session directory:

```bash
CLAUDE_PROJECTS_DIR=/path/to/projects ./scripts/install.sh
```

The installer validates Docker and the session path, writes mode-`0600`
runtime configuration, builds the image, starts the fixed `locallore` Compose
project, waits for indexing, and runs production checks.

Load a checkout as a development plugin with:

```bash
claude --plugin-dir .
```

## Inspect the service

```bash
./scripts/status.sh
./scripts/logs.sh
./scripts/doctor.sh
```

`status.sh` summarizes container and index state. `logs.sh` follows daemon
output. `doctor.sh` validates configuration, migrations, FTS5, model inference,
container count, loopback publication, and Host/Origin protection.

The daemon persists across normal Claude sessions. If it has been stopped,
rerun `/locallore:setup` or `./scripts/install.sh`.

## Preview this documentation

Install the locked documentation dependencies and start the development server:

```bash
uv sync --locked --group docs
uv run --group docs mkdocs serve
```

Then open `http://127.0.0.1:8000/`. Validate the production build with:

```bash
uv run --group docs mkdocs build --strict
```

## Uninstall

```bash
./scripts/uninstall.sh
```

The script asks before deleting the container, derived index volume, and
runtime configuration. It does not delete Claude session files.
