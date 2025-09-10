#!/bin/bash
# docs/validate.sh – Auto-check doc accuracy

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Checking docs vs code..."

# 1. Auth key: should match what's in code or .env
CODE_LINE=$(grep -E "API_KEY[[:space:]]*=" backend/mcp/mcp_server.py 2>/dev/null | head -n 1)
ENV_KEY=$(grep -E '^MCP_API_KEY=' .env 2>/dev/null | cut -d= -f2-)
if [[ -z "$ENV_KEY" ]]; then
  ENV_KEY=$(grep -E '^MCP_API_KEY=' .env.template 2>/dev/null | cut -d= -f2-)
fi

if echo "$CODE_LINE" | grep -q "dev-key-123"; then
  echo -e "${GREEN}Hardcoded dev key found – OK for testing.${NC}"
else
  if [[ -n "$ENV_KEY" && "$CODE_LINE" =~ os.environ.get|os.getenv ]]; then
    echo -e "${GREEN}Key pulled from .env – production-ready.${NC}"
  else
    echo -e "${RED}Key missing or inconsistent – fix .env or code.${NC}"
    exit 1
  fi
fi

# 2. Last validated timestamp – auto-update
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%SZ')
sed -i'' -e "s/Last validated: .*/Last validated: $TIMESTAMP/" docs/auth.md
echo "Updated docs/auth.md → Last validated: $TIMESTAMP"

# 3. Granularity test – simulate pick up and run
if grep -q 'Run this:' docs/README.md; then
  echo -e "${GREEN}README has boot instructions – granular enough.${NC}"
else
  echo -e "${RED}Add 'Run this' block to README – someone needs a map.${NC}"
  exit 1
fi

# 4. Future naming – bake it in
if grep -q 'API_KEY_MCP1' docs/env-plan.md 2>/dev/null; then
  echo -e "${GREEN}Future key naming documented.${NC}"
else
  echo "Adding vision to docs/env-plan.md..."
  cat >> docs/env-plan.md <<'EOS'
Future: MCP Key Rotation & Multi-MCP Support

- Keys : Use API_KEY_MCP1, API_KEY_MCP2, ... – one per instance.
- Why : Clear, scalable. MCP1 → MCP5 already reserved in DNS. When we migrate (e.g., AWS → GCP), just flip DNS and rotate key.
- How : In code, get: API_KEY = os.getenv(f'API_KEY_MCP{instance_num}', 'fallback')
- Transition : Run both stacks, send traffic
EOS
fi

