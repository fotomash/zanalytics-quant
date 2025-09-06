# UI Components

## `pulse_client.py`

`pulse_client.py` provides a small asynchronous client for interacting with the Pulse API. It exposes helper functions for scoring symbols, calculating risk, and journaling trade entries.

### Configuration

The client reads the `PULSE_API_URL` environment variable to determine the base URL of the Pulse API. If unset, it defaults to `http://localhost:8080`.

### Streamlit usage

These helpers are designed to be called inside Streamlit callbacks. The example below fetches a score for `EURUSD` when a button is pressed.

```python
import asyncio
import streamlit as st
from ui.pulse_client import score

async def handle_score():
    data = await score("EURUSD")
    st.json(data)

if st.button("Score"):
    asyncio.run(handle_score())
```

### API Version

This client targets **Pulse API version 1.0.0**.
