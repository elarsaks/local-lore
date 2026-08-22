# LocalLore 0.3.0 Release Notes

LocalLore 0.3.0 adds self-hosted Claude Code marketplace distribution and an
in-plugin setup command for provisioning or updating the persistent daemon.

## Marketplace installation

Install LocalLore from its GitHub repository:

```text
/plugin marketplace add elarsaks/local-lore
/plugin install locallore@locallore
/reload-plugins
/locallore:setup
```

The marketplace catalog pins the plugin to version 0.3.0. Marketplace installs
use the standard Claude projects directory (`~/.claude/projects`) and loopback
port (`8765`) automatically instead of prompting for configuration. The setup
command passes the persistent plugin data directory to the installer, builds the
versioned container image, starts the daemon, waits for initial indexing, and
runs the production health and security checks.

Rerun `/locallore:setup` after marketplace updates to build and activate the
matching daemon version.

## Existing installations

Checkout-based installations remain supported with:

```bash
./scripts/install.sh
```

The installer preserves the runtime configuration and migrates the SQLite
database in place. The three MCP tool names and input schemas are unchanged.

## Security and networking

The endpoint remains loopback-only with Host/Origin protection. Session history
is mounted read-only, and inference uses only the model bundled in the image.
LocalLore makes no runtime network requests, but the standard Docker bridge
allows outbound connectivity at the container boundary; this release does not
claim Docker-enforced egress isolation.

Previous release: [LocalLore 0.2.0](docs/releases/v0.2.0.md).
