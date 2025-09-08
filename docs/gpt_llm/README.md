# Whisperer Loader Notes

- `whisperer_zanflow_master.yaml` lists KBs by filename only (portable for flat uploads).
- The loader (`utils/loader_utils.py`) automatically resolves KB paths relative to the master YAML location:
  - Same directory as the master file
  - `behavioral/`, `strategy/`, `support/`, `constitutional/` subfolders

This means you can run either layout without changing the YAML:

- Flat upload (all files next to the master YAML)
- Full extracted pack at `docs/gpt_llm/whisperer_zanflow_pack/`

Example usage in your orchestrator:

```python
from utils.loader_utils import load_master_config

master_cfg = load_master_config(
    "docs/gpt_llm/whisperer_zanflow_pack/whisperer_zanflow_master.yaml"
)
kb_files = master_cfg["knowledge_bases_resolved"]

for kb in kb_files:
    # Attach each KB into the GPT context
    print("Loaded KB:", kb)
```

Tip: Keep the GPT system prompt slim (see `docs/gpt_llm/whisperer_gpt_instructions.yaml`) and let the master config + ActionBus power the boot sequence (default `session_boot`).

