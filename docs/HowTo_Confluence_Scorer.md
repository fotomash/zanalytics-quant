# Confluence Scorer How-To

This guide shows how to generate multi-strategy confluence scores and how to interact with the Whisperer from the dashboard.

## Using the Confluence Scorer

The Confluence Scorer blends Smart Money Concepts (SMC), Wyckoff, and traditional technical signals into a single rating.

1. **Prepare market data** as a pandas DataFrame or a normalized dictionary of price series.
2. **Instantiate the scorer**:
   ```python
   from confluence_scorer import ConfluenceScorer
   scorer = ConfluenceScorer()
   ```
3. **Generate a score**:
   ```python
   result = scorer.score(market_data)
   print(result["score"], result["grade"])
   ```
4. **Interpret the output**:
   - `score`: numeric 0–100 rating.
   - `grade`: `high`, `medium`, or `low` based on thresholds.
   - `components`: individual scores for SMC, Wyckoff, and technical modules.
   - `reasons`: textual explanation for the final rating.

Weights and thresholds are configurable in `pulse_config.yaml`.

## Whisperer Interaction Tips

The Whisperer offers quick, context-aware coaching in the dashboard sidebar.

- Keep questions concise and, when relevant, include the trading symbol.
- Use the suggested prompts in the sidebar to learn expected inputs and responses.
- Replies follow a `Signal • Risk • Action • Journal` structure to help drive decisions.
- Acknowledge or act on guidance through the appropriate API endpoints to refine future suggestions.

For deeper details see `docs/WHISPERER.md`.
