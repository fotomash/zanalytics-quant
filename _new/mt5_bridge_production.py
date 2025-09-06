"""
MT5 Bridge - Production-Ready with Precision Fixes
Real trade history integration for Pulse UI with proper behavioral analytics
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import yaml

# Timezone constants
LONDON = pytz.timezone("Europe/London")
UTC = pytz.UTC

class MT5Bridge:
    """
    Production-ready bridge between MT5 and Pulse system.
    Handles real trade history with precise behavioral analytics.
    """

    def __init__(self, account: int | None = None, password: str | None = None, server: str | None = None):
        """Initialize MT5 connection parameters."""
        self.account = account
        self.password = password  # FIX: Actually store the password
        self.server = server      # FIX: Actually store the server
        self.connected = False
        self.trade_cache = {}
        self.behavioral_patterns = {}

    def connect(self) -> bool:
        """Establish connection to MT5 with proper error handling."""
        try:
            # Initialize MT5
            if not mt5.initialize():
                print("MT5 initialization failed")
                return False

            # Optional login (if account provided)
            if self.account:
                if not mt5.login(self.account, password=self.password, server=self.server):
                    print(f"Login failed for account {self.account}")
                    mt5.shutdown()
                    return False

            self.connected = True
            print(f"Successfully connected to MT5{f' account {self.account}' if self.account else ''}")
            return True

        except Exception as e:
            print(f"Connection error: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Safely disconnect from MT5."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("Disconnected from MT5")

    def get_real_trade_history(self, days_back: int = 30) -> pd.DataFrame:
        """
        Fetch real trade history from MT5 with proper timezone handling.

        Returns:
            DataFrame with actual trades and behavioral analysis
        """
        if not self.connected:
            raise ConnectionError("Not connected to MT5")

        # Get deals from history
        from_date = datetime.now() - timedelta(days=days_back)
        deals = mt5.history_deals_get(from_date, datetime.now())

        if deals is None or len(deals) == 0:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())

        # FIX: Proper timezone conversion
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert(LONDON)
        df['date'] = df['time'].dt.date
        df['hour_local'] = df['time'].dt.hour

        # Sort by time for proper sequential analysis
        df = df.sort_values('time')

        # Process and enrich with behavioral data
        df = self._enrich_with_behavioral_data(df)

        return df

    def _enrich_with_behavioral_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich trade history with precise behavioral analysis.
        All calculations are scoped per symbol/day to avoid false signals.
        """
        if df.empty:
            return df

        # Win/loss flag
        df['is_win'] = df['profit'] > 0

        # FIX: Proper streak calculation per symbol/day
        def calculate_streaks(x: pd.Series) -> pd.Series:
            """Calculate consecutive wins (positive values when winning, 0 otherwise)"""
            groups = (x != x.shift()).cumsum()
            run = x.groupby(groups).cumcount() + 1
            return run.where(x, 0)

        def calculate_loss_streaks(x: pd.Series) -> pd.Series:
            """Calculate consecutive losses (positive values when losing, 0 otherwise)"""
            groups = (x != x.shift()).cumsum()
            run = (~x).groupby(groups).cumcount() + 1
            return run.where(~x, 0)

        # Apply streak calculations per symbol and date
        df['consecutive_wins'] = df.groupby(['symbol', 'date'], group_keys=False)['is_win'].apply(calculate_streaks)
        df['consecutive_losses'] = df.groupby(['symbol', 'date'], group_keys=False)['is_win'].apply(calculate_loss_streaks)

        # FIX: Time since last trade per symbol/day
        df['time_since_last'] = df.groupby(['symbol', 'date'])['time'].diff()

        # FIX: Revenge trading - scoped to symbol/day
        df['prev_loss'] = df.groupby(['symbol', 'date'])['profit'].shift().lt(0)
        df['revenge_trade'] = df['prev_loss'] & (df['time_since_last'] < pd.Timedelta(minutes=15))

        # FIX: Overconfidence - position size change per symbol/day
        df['position_change'] = df.groupby(['symbol', 'date'])['volume'].pct_change()
        df['overconfidence'] = (df['consecutive_wins'] >= 3) & (df['position_change'] > 0.5)

        # FIX: FOMO detection - fast re-entries per symbol/day
        df['entry_speed_s'] = df['time_since_last'].dt.total_seconds()
        df['fomo_trade'] = df['entry_speed_s'].fillna(1e9) < 60

        # FIX: Fatigue - running count within day
        df['trade_index_today'] = df.groupby('date').cumcount() + 1
        df['fatigue_trade'] = df['trade_index_today'] > 5

        # FIX: Optimal time using localized hour
        df['is_optimal_time'] = df['hour_local'].between(8, 20)  # London/NY sessions

        # FIX: Daily P&L and drawdown calculation
        df['daily_pnl'] = df.groupby('date')['profit'].cumsum()
        df['daily_drawdown'] = df.groupby('date')['daily_pnl'].cummin()

        # FIX: Behavioral risk score with NaN safety
        flags = ['revenge_trade', 'overconfidence', 'fatigue_trade', 'fomo_trade', 'is_optimal_time']
        for flag in flags:
            df[flag] = df[flag].fillna(False)

        df['behavioral_risk_score'] = (
            df['revenge_trade'].astype(int) * 3 +
            df['overconfidence'].astype(int) * 2 +
            df['fatigue_trade'].astype(int) * 2 +
            df['fomo_trade'].astype(int) * 1 +
            (~df['is_optimal_time']).astype(int) * 1
        ).clip(0, 10)

        return df

    def get_behavioral_report(self) -> Dict:
        """
        Generate comprehensive behavioral analysis report with proper error handling.
        """
        try:
            df = self.get_real_trade_history()

            if df.empty:
                return {"error": "No trade history available"}

            # FIX: Safe profit factor calculation
            wins = df.loc[df['is_win'], 'profit'].sum()
            losses = df.loc[~df['is_win'], 'profit'].sum()
            profit_factor = float('inf') if losses == 0 else abs(wins / losses) if losses != 0 else 0

            # FIX: Safe mode calculation for fatigue trades
            fatigue_hours = df.loc[df['fatigue_trade'], 'hour_local']
            typical_fatigue_time = fatigue_hours.mode().iloc[0] if not fatigue_hours.empty and not fatigue_hours.mode().empty else None

            report = {
                "performance_metrics": {
                    "total_trades": len(df),
                    "win_rate": (df['is_win'].sum() / len(df) * 100) if len(df) > 0 else 0,
                    "avg_win": df[df['is_win']]['profit'].mean() if df['is_win'].any() else 0,
                    "avg_loss": df[~df['is_win']]['profit'].mean() if (~df['is_win']).any() else 0,
                    "profit_factor": profit_factor,
                    "max_consecutive_wins": df['consecutive_wins'].max(),
                    "max_consecutive_losses": df['consecutive_losses'].max(),
                    "total_pnl": df['profit'].sum()
                },
                "behavioral_patterns": {
                    "revenge_trades": {
                        "count": int(df['revenge_trade'].sum()),
                        "success_rate": df[df['revenge_trade']]['is_win'].mean() * 100 if df['revenge_trade'].any() else 0,
                        "avg_loss": df[df['revenge_trade'] & ~df['is_win']]['profit'].mean() if (df['revenge_trade'] & ~df['is_win']).any() else 0
                    },
                    "overconfidence_trades": {
                        "count": int(df['overconfidence'].sum()),
                        "success_rate": df[df['overconfidence']]['is_win'].mean() * 100 if df['overconfidence'].any() else 0,
                        "avg_result": df[df['overconfidence']]['profit'].mean() if df['overconfidence'].any() else 0
                    },
                    "fatigue_trades": {
                        "count": int(df['fatigue_trade'].sum()),
                        "success_rate": df[df['fatigue_trade']]['is_win'].mean() * 100 if df['fatigue_trade'].any() else 0,
                        "typical_time": typical_fatigue_time
                    },
                    "fomo_trades": {
                        "count": int(df['fomo_trade'].sum()),
                        "avg_loss": df[df['fomo_trade'] & ~df['is_win']]['profit'].mean() if (df['fomo_trade'] & ~df['is_win']).any() else 0
                    }
                },
                "time_analysis": {
                    "best_hours": df.groupby('hour_local')['profit'].sum().nlargest(3).to_dict(),
                    "worst_hours": df.groupby('hour_local')['profit'].sum().nsmallest(3).to_dict(),
                    "trades_by_hour": df.groupby('hour_local').size().to_dict()
                },
                "risk_violations": {
                    "overtrade_days": len(df.groupby('date').size()[df.groupby('date').size() > 5]),
                    "max_daily_trades": df.groupby('date').size().max() if not df.empty else 0,
                    "drawdown_breaches": len(df[df['daily_drawdown'] < -300])  # $300 daily limit
                }
            }

            return report

        except Exception as e:
            return {"error": f"Report generation failed: {str(e)}"}

    def attach_real_confluence_scores(self, df: pd.DataFrame, journal_path: str = "signal_journal.json") -> pd.DataFrame:
        """
        Attach real confluence scores from signal journal instead of random values.

        Args:
            df: Trade history DataFrame
            journal_path: Path to signal journal file

        Returns:
            DataFrame with real confluence scores attached
        """
        try:
            # Load signal journal
            with open(journal_path, 'r') as f:
                journal = json.load(f)

            # Extract scores with timestamps
            scores = []
            for entry in journal:
                if entry.get('type') == 'analysis' and 'confluence_score' in entry.get('data', {}):
                    scores.append({
                        'ts': entry['timestamp'],
                        'symbol': entry['data'].get('symbol', 'UNKNOWN'),
                        'score': entry['data']['confluence_score']
                    })

            if not scores:
                # No scores found, return df unchanged
                df['confluence_score'] = np.nan
                return df

            # Convert to DataFrame
            scores_df = pd.DataFrame(scores)
            scores_df['ts'] = pd.to_datetime(scores_df['ts'], utc=True).dt.tz_convert(LONDON)

            # Merge scores with trades (nearest match within 5 minutes)
            df = pd.merge_asof(
                df.sort_values('time'),
                scores_df.sort_values('ts'),
                left_on='time',
                right_on='ts',
                by='symbol',
                direction='backward',
                tolerance=pd.Timedelta(minutes=5)
            )

            # Fill missing scores with NaN (not random!)
            df['confluence_score'] = df.get('score', np.nan)

            return df

        except FileNotFoundError:
            df['confluence_score'] = np.nan
            return df
        except Exception as e:
            print(f"Error attaching confluence scores: {e}")
            df['confluence_score'] = np.nan
            return df

    def get_confluence_validation(self, journal_path: str = "signal_journal.json") -> pd.DataFrame:
        """
        Validate historical confluence scores against actual outcomes using REAL scores.
        """
        df = self.get_real_trade_history()

        if df.empty:
            return pd.DataFrame()

        # FIX: Attach real confluence scores from journal
        df = self.attach_real_confluence_scores(df, journal_path)

        # Only validate trades with known scores
        df_with_scores = df[df['confluence_score'].notna()]

        if df_with_scores.empty:
            print("No trades with confluence scores found for validation")
            return pd.DataFrame()

        # Bin confluence scores
        df_with_scores['confluence_band'] = pd.cut(
            df_with_scores['confluence_score'],
            bins=[0, 50, 60, 70, 80, 90, 100],
            labels=['<50', '50-60', '60-70', '70-80', '80-90', '90+']
        )

        # Calculate win rate by confluence band
        validation = df_with_scores.groupby('confluence_band').agg({
            'is_win': ['count', 'mean'],
            'profit': ['sum', 'mean']
        }).round(2)

        validation.columns = ['trades', 'win_rate', 'total_pnl', 'avg_pnl']
        validation['win_rate'] = validation['win_rate'] * 100

        return validation

    def sync_to_pulse_journal(self, journal_path: str = "signal_journal.json") -> int:
        """
        Sync MT5 trade history with Pulse signal journal (idempotent).
        """
        df = self.get_real_trade_history()

        if df.empty:
            return 0

        # Load existing journal
        try:
            with open(journal_path, 'r') as f:
                journal = json.load(f)
        except FileNotFoundError:
            journal = []

        # Track existing tickets to avoid duplicates
        existing_tickets = {
            entry['data'].get('ticket')
            for entry in journal
            if entry.get('type') == 'mt5_trade' and 'ticket' in entry.get('data', {})
        }

        new_entries = 0

        # Convert trades to journal entries
        for _, trade in df.iterrows():
            ticket = int(trade.get('ticket', 0))

            # Skip if already exists (idempotent)
            if ticket in existing_tickets:
                continue

            entry = {
                "timestamp": trade['time'].isoformat(),
                "type": "mt5_trade",
                "data": {
                    "ticket": ticket,
                    "symbol": str(trade.get('symbol', 'UNKNOWN')),
                    "volume": float(trade.get('volume', 0)),
                    "profit": float(trade.get('profit', 0)),
                    "is_win": bool(trade.get('is_win', False)),
                    "behavioral_flags": {
                        "revenge_trade": bool(trade.get('revenge_trade', False)),
                        "overconfidence": bool(trade.get('overconfidence', False)),
                        "fatigue_trade": bool(trade.get('fatigue_trade', False)),
                        "fomo_trade": bool(trade.get('fomo_trade', False))
                    },
                    "behavioral_risk_score": int(trade.get('behavioral_risk_score', 0)),
                    "consecutive_wins": int(trade.get('consecutive_wins', 0)),
                    "consecutive_losses": int(trade.get('consecutive_losses', 0)),
                    "hour_local": int(trade.get('hour_local', 0)),
                    "is_optimal_time": bool(trade.get('is_optimal_time', False))
                }
            }

            journal.append(entry)
            new_entries += 1

        # Save updated journal (keep last 10000 entries)
        with open(journal_path, 'w') as f:
            json.dump(journal[-10000:], f, indent=2, default=str)

        print(f"Synced {new_entries} new entries to journal")
        return new_entries

    def generate_weekly_review(self) -> Dict:
        """
        Generate weekly performance and behavioral review with actionable insights.
        """
        df = self.get_real_trade_history(days_back=7)

        if df.empty:
            return {"error": "No trades this week"}

        # Best and worst day calculations
        daily_pnl = df.groupby('date')['profit'].sum()
        best_day = daily_pnl.idxmax() if not daily_pnl.empty else None
        worst_day = daily_pnl.idxmin() if not daily_pnl.empty else None

        review = {
            "week_ending": datetime.now().strftime("%Y-%m-%d"),
            "summary": {
                "total_trades": len(df),
                "total_pnl": float(df['profit'].sum()),
                "win_rate": float(df['is_win'].mean() * 100) if len(df) > 0 else 0,
                "best_day": best_day.strftime("%Y-%m-%d") if best_day else "N/A",
                "worst_day": worst_day.strftime("%Y-%m-%d") if worst_day else "N/A",
                "avg_risk_score": float(df['behavioral_risk_score'].mean())
            },
            "behavioral_insights": {
                "revenge_trading_incidents": int(df['revenge_trade'].sum()),
                "overconfidence_incidents": int(df['overconfidence'].sum()),
                "fatigue_incidents": int(df['fatigue_trade'].sum()),
                "fomo_incidents": int(df['fomo_trade'].sum()),
                "suboptimal_time_trades": int((~df['is_optimal_time']).sum())
            },
            "recommendations": []
        }

        # Generate personalized recommendations based on actual patterns
        if df['revenge_trade'].sum() > 2:
            review["recommendations"].append(
                f"Implement mandatory 30-min cooldown after losses (you had {df['revenge_trade'].sum()} revenge trades)"
            )

        if df['overconfidence'].sum() > 3:
            review["recommendations"].append(
                f"Reduce position size by 50% after 3 consecutive wins (overconfidence detected {df['overconfidence'].sum()} times)"
            )

        if df['fatigue_trade'].sum() > 5:
            review["recommendations"].append(
                f"Hard limit at 5 trades/day (you exceeded this {df[df['trade_index_today'] > 5]['date'].nunique()} days)"
            )

        if (~df['is_optimal_time']).sum() > len(df) * 0.3:
            review["recommendations"].append(
                f"Restrict trading to 08:00-20:00 London time ({(~df['is_optimal_time']).sum()} trades outside optimal hours)"
            )

        if df['fomo_trade'].sum() > 3:
            review["recommendations"].append(
                f"Minimum 2-minute wait between trades on same symbol ({df['fomo_trade'].sum()} FOMO trades detected)"
            )

        return review


# Example usage showing production readiness
if __name__ == "__main__":
    # Initialize with credentials (these would come from secure config)
    bridge = MT5Bridge(
        account=12345,  # Replace with actual
        password="your_password",  # From secure storage
        server="YourBroker-Server"  # From config
    )

    # Connect with error handling
    if bridge.connect():
        try:
            # Get behavioral report
            report = bridge.get_behavioral_report()
            print(json.dumps(report, indent=2, default=str))

            # Validate confluence scores
            validation = bridge.get_confluence_validation()
            print("\nConfluence Validation:")
            print(validation)

            # Generate weekly review
            review = bridge.generate_weekly_review()
            print("\nWeekly Review:")
            print(json.dumps(review, indent=2))

            # Sync to journal
            synced = bridge.sync_to_pulse_journal()
            print(f"\nSynced {synced} trades to journal")

        finally:
            # Always disconnect cleanly
            bridge.disconnect()
    else:
        print("Failed to connect to MT5")
