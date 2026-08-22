# LocalLore 0.3.1 Release Notes

LocalLore 0.3.1 simplifies the persistent local runtime and removes bearer-token
authentication from its loopback-only MCP endpoint.

## Simpler local connection

- Claude Code now connects directly to `http://127.0.0.1:8765/mcp` without a
  token or headers helper.
- The endpoint remains published only on `127.0.0.1`.
- HTTP Host and Origin validation remains enabled to protect against browser and
  DNS-rebinding requests.
- Local processes running as the current user are trusted and can access
  LocalLore without authentication.

The release also removes unused port configurability, the unused manual refresh
endpoint, redundant watcher state, self-reported network metadata, and duplicate
Docker environment configuration. The MCP tool names and input schemas are
unchanged.

## Install or update

The marketplace catalog publishes LocalLore 0.3.1. Install it from its GitHub
repository:

```text
/plugin marketplace add elarsaks/local-lore
/plugin install locallore@locallore
/reload-plugins
/locallore:setup
```

Rerun `/locallore:setup` after updating an existing marketplace installation.
Checkout-based installations remain supported with:

```bash
./scripts/install.sh
```

The setup command builds the versioned container image, starts the daemon, waits
for initial indexing, and verifies the loopback binding and Host/Origin
protection.

## Privacy and networking

Session history remains mounted read-only, and inference uses only the model
bundled in the image. LocalLore makes no runtime network requests, but the
default Compose bridge allows outbound connectivity at the container boundary;
this release does not claim Docker-enforced egress isolation.

Previous release: [LocalLore 0.3.0](https://github.com/elarsaks/local-lore/releases/tag/v0.3.0).
