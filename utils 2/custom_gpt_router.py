
"""
ZANFLOW Custom GPT Router
Routes specific analysis types to specialized GPT models
"""

import streamlit as st
from typing import Dict, List, Optional
import openai
import json

class CustomGPTRouter:
    """Routes analysis to specialized GPT models"""

    def __init__(self):
        self.gpt_configs = {
            "smc_specialist": {
                "model": "gpt-4-turbo-preview",
                "system_prompt": """You are a Smart Money Concepts specialist. Focus on:
                - Order blocks and fair value gaps
                - Liquidity sweeps and inducement
                - Break of structure patterns
                - Institutional order flow"""
            },
            "wyckoff_specialist": {
                "model": "gpt-4-turbo-preview", 
                "system_prompt": """You are a Wyckoff methodology expert. Analyze:
                - Accumulation and distribution phases
                - Spring and upthrust patterns
                - Volume and price relationships
                - Composite operator behavior"""
            },
            "risk_manager": {
                "model": "gpt-4-turbo-preview",
                "system_prompt": """You are a professional risk manager. Calculate:
                - Optimal position sizing
                - Stop loss placement
                - Risk/reward ratios
                - Portfolio heat analysis"""
            },
            "macro_analyst": {
                "model": "gpt-4-turbo-preview",
                "system_prompt": """You are a macro market analyst. Consider:
                - Inter-market relationships
                - Economic indicators
                - Sentiment analysis
                - Geopolitical factors"""
            }
        }

    async def route_analysis(self, analysis_type: str, data: Dict) -> Dict:
        """Route to appropriate GPT based on analysis type"""

        config = self.gpt_configs.get(analysis_type, self.gpt_configs["smc_specialist"])

        messages = [
            {"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": json.dumps(data)}
        ]

        try:
            response = openai.ChatCompletion.create(
                model=config["model"],
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return {
                "specialist": analysis_type,
                "analysis": response.choices[0].message.content,
                "confidence": self._extract_confidence(response.choices[0].message.content)
            }

        except Exception as e:
            return {
                "specialist": analysis_type,
                "error": str(e),
                "analysis": "Failed to get specialist analysis"
            }

    async def get_consensus_analysis(self, data: Dict) -> Dict:
        """Get analysis from all specialists and form consensus"""

        analyses = {}

        # Get analysis from each specialist
        for specialist in self.gpt_configs.keys():
            analyses[specialist] = await self.route_analysis(specialist, data)

        # Form consensus
        consensus = self._form_consensus(analyses)

        return {
            "individual_analyses": analyses,
            "consensus": consensus
        }

    def _form_consensus(self, analyses: Dict) -> Dict:
        """Form consensus from multiple specialist analyses"""

        # Extract key points from each analysis
        bullish_count = 0
        bearish_count = 0
        confidence_scores = []

        for specialist, analysis in analyses.items():
            if "error" not in analysis:
                # Simple sentiment extraction (enhance this)
                content = analysis.get("analysis", "").lower()
                if "bullish" in content or "buy" in content or "long" in content:
                    bullish_count += 1
                elif "bearish" in content or "sell" in content or "short" in content:
                    bearish_count += 1

                if "confidence" in analysis:
                    confidence_scores.append(analysis["confidence"])

        # Calculate consensus
        total_votes = bullish_count + bearish_count
        if total_votes > 0:
            bullish_percentage = (bullish_count / total_votes) * 100
        else:
            bullish_percentage = 50

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 50

        bias = "BULLISH" if bullish_percentage > 60 else "BEARISH" if bullish_percentage < 40 else "NEUTRAL"

        return {
            "bias": bias,
            "bullish_percentage": bullish_percentage,
            "average_confidence": avg_confidence,
            "specialist_agreement": "HIGH" if abs(bullish_percentage - 50) > 30 else "MEDIUM" if abs(bullish_percentage - 50) > 15 else "LOW"
        }

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from analysis text"""
        # Simple implementation - enhance with better NLP
        confidence_keywords = {
            "very confident": 90,
            "highly confident": 85,
            "confident": 75,
            "somewhat confident": 60,
            "uncertain": 40,
            "low confidence": 30
        }

        text_lower = text.lower()
        for keyword, score in confidence_keywords.items():
            if keyword in text_lower:
                return score

        return 50  # Default confidence

# Integration with main system
def integrate_gpt_router(main_analysis: Dict) -> Dict:
    """Integrate GPT router with main analysis"""

    router = CustomGPTRouter()

    # Prepare data for specialists
    specialist_data = {
        "market_data": main_analysis.get("market_data", {}),
        "technical_indicators": main_analysis.get("indicators", {}),
        "patterns": main_analysis.get("patterns", {})
    }

    # Get consensus analysis
    consensus = asyncio.run(router.get_consensus_analysis(specialist_data))

    return consensus
