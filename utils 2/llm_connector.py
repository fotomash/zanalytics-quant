import requests
import json
from datetime import datetime

class MicrostructureLLMConnector:
    """Connect dashboard to LLM for analysis"""

    def __init__(self, api_endpoint, api_key):
        self.endpoint = api_endpoint
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def analyze_manipulation(self, dashboard_data):
        """Send manipulation data to LLM for analysis"""

        prompt = f"""
        Analyze the following market microstructure data:

        Time Period: {dashboard_data.get('timestamp')}
        Total Records: {dashboard_data.get('records')}

        Manipulation Events:
        - Spoofing: {dashboard_data['manipulation_events']['spoofing']}
        - Wash Trading: {dashboard_data['manipulation_events']['wash_trading']}

        Spread Statistics:
        - Mean: {dashboard_data['spread_stats']['mean']:.4f}
        - Std Dev: {dashboard_data['spread_stats']['std']:.4f}
        - Max: {dashboard_data['spread_stats']['max']:.4f}

        Provide:
        1. Risk assessment
        2. Trading recommendations
        3. Market manipulation severity
        4. Suggested actions
        """

        payload = {
            "messages": [
                {"role": "system", "content": "You are a market microstructure expert."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post(self.endpoint, json=payload, headers=self.headers)
        return response.json()

    def get_smc_insights(self, smc_data):
        """Get Smart Money Concepts insights from LLM"""

        prompt = f"""
        Analyze Smart Money Concepts data:

        Market Structure: {smc_data.get('trend')}
        Liquidity Zones: {smc_data.get('liquidity_zones')}
        Order Blocks: {smc_data.get('order_blocks')}
        Fair Value Gaps: {smc_data.get('fair_value_gaps')}

        Identify:
        1. Institutional positioning
        2. Key levels to watch
        3. Potential manipulation zones
        4. Entry/exit recommendations
        """

        payload = {
            "messages": [
                {"role": "system", "content": "You are a Smart Money Concepts expert."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post(self.endpoint, json=payload, headers=self.headers)
        return response.json()

# Example usage
if __name__ == "__main__":
    # Initialize connector
    connector = MicrostructureLLMConnector(
        api_endpoint="https://your-gpt-api.com/v1/chat/completions",
        api_key="your-api-key"
    )

    # Sample dashboard data
    dashboard_data = {
        "timestamp": "2025-07-04T10:30:00",
        "records": 1000,
        "manipulation_events": {
            "spoofing": 5,
            "wash_trading": 3
        },
        "spread_stats": {
            "mean": 0.25,
            "std": 0.05,
            "max": 0.45
        }
    }

    # Get analysis
    analysis = connector.analyze_manipulation(dashboard_data)
    print(json.dumps(analysis, indent=2))
