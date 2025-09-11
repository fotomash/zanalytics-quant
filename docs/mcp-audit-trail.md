# MCP Audit Trail

## Removal of ghost `whisperer-mcp` service

The `whisperer-mcp` container defined in `docker-compose.yml` was identified as an
unused "ghost" service during infrastructure cleanup. The endpoint it targeted is
no longer maintained and no other services depend on it.

To avoid confusion and reduce image build time, the service was removed from the
compose file and replaced with an explanatory comment. This document records the
change for future reference.
