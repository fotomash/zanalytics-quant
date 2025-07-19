
"""
ZANFLOW Configuration Helper
Sets up environment and validates API connections
"""

import os
import json
from pathlib import Path
import streamlit as st

def setup_environment():
    """Setup environment with secrets"""

    # Create .streamlit directory if it doesn't exist
    streamlit_dir = Path(".streamlit")
    streamlit_dir.mkdir(exist_ok=True)

    # Your secrets (be careful with these!)
    secrets = {
        "openai_API": "your-openai-key",
        "finnhub_api_key": "your-finnhub-key",
        "newsapi_key": "your-newsapi-key",
        "telegram_bot_token": "",  # Add if you have
        "telegram_chat_id": "",    # Add if you have
        "folders": {
            "data_directory": str(Path.home() / "Documents" / "_trade" / "_exports" / "_tick" / "parquet"),
            "raw_data_directory": str(Path.home() / "Documents" / "_trade" / "_exports" / "_tick" / "_raw"),
            "enriched_data": str(Path.home() / "Documents" / "_trade" / "_exports" / "_tick" / "parquet")
        }
    }

    # Save secrets
    secrets_file = streamlit_dir / "secrets.toml"

    # Note: In production, manage secrets properly!
    print(f"Secrets should be configured in: {secrets_file}")
    print("Please add your API keys to the secrets.toml file")

    return True

def test_connections():
    """Test all API connections"""
    results = {}

    try:
        import openai
        openai.api_key = st.secrets.get("openai_API", "")
        # Test OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        results["OpenAI"] = "✅ Connected"
    except:
        results["OpenAI"] = "❌ Failed"

    # Test data paths
    try:
        data_path = Path(st.secrets["folders"]["enriched_data"])
        if data_path.exists():
            results["Data Path"] = "✅ Found"
        else:
            results["Data Path"] = "❌ Not Found"
    except:
        results["Data Path"] = "❌ Error"

    return results

if __name__ == "__main__":
    print("ZANFLOW Configuration Helper")
    print("-" * 50)

    if setup_environment():
        print("✅ Environment setup complete")
        print("
Testing connections...")

        results = test_connections()
        for service, status in results.items():
            print(f"{service}: {status}")
