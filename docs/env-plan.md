Future: MCP Key Rotation & Multi-MCP Support

- Keys : Use API_KEY_MCP1, API_KEY_MCP2, ... – one per instance.
- Why : Clear, scalable. MCP1 → MCP5 already reserved in DNS. When we migrate (e.g., AWS → GCP), just flip DNS and rotate key.
- How : In code, get: API_KEY = os.getenv(f'API_KEY_MCP{instance_num}', 'fallback')
- Transition : Run both stacks, send traffic
