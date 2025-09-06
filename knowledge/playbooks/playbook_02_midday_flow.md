# Pull the latest bar from /api/pulse/score every 15 min
# Apply RiskEnforcer checks (daily-loss, max-trades)
# If score > score_threshold (55 by default), send a "rebalance" command to the execution engine
