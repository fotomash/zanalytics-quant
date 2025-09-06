# Load latest snapshot from Kafka (mt5.ticks topic)
# Run SMCAnalyzer & WyckoffAnalyzer on the first 5 min of bars
# Compute Confluence score using hybrid_confluence.yaml
# Persist score to the Signal Journal and emit a /pulse/open event
