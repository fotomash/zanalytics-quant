# ncOS Theory Backtesting Module

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json

class TheoryBacktester:
    """Backtest the integrated trading theories"""
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.equity_curve = []
        self.statistics = {}
        
    def backtest_strategy(self, 
                         data: pd.DataFrame,
                         engine,
                         risk_per_trade: float = 0.01,
                         max_concurrent: int = 3) -> Dict:
        """
        Backtest the complete strategy
        
        Args:
            data: OHLCV data with volume
            engine: AdvancedTheoryEngine instance
            risk_per_trade: Risk percentage per trade
            max_concurrent: Maximum concurrent positions
        """
        
        # Reset state
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]
        
        open_positions = []
        
        # Iterate through data
        for i in range(100, len(data)):  # Start after warmup period
            current_data = data.iloc[:i]
            current_price = data.iloc[i]['close']
            current_time = data.iloc[i]['timestamp']
            
            # Check for exits on open positions
            positions_to_close = []
            
            for pos in open_positions:
                # Check stop loss
                if pos['direction'] == 'long' and current_price <= pos['stop_loss']:
                    pos['exit_price'] = pos['stop_loss']
                    pos['exit_time'] = current_time
                    pos['exit_reason'] = 'Stop Loss'
                    positions_to_close.append(pos)
                    
                elif pos['direction'] == 'short' and current_price >= pos['stop_loss']:
                    pos['exit_price'] = pos['stop_loss']
                    pos['exit_time'] = current_time
                    pos['exit_reason'] = 'Stop Loss'
                    positions_to_close.append(pos)
                    
                # Check take profits
                else:
                    for tp_idx, tp in enumerate(pos['take_profits']):
                        if pos['direction'] == 'long' and current_price >= tp:
                            if f'tp{tp_idx+1}_hit' not in pos:
                                pos[f'tp{tp_idx+1}_hit'] = True
                                # Partial exit logic
                                if tp_idx == 0:  # TP1
                                    pos['remaining_size'] *= 0.5
                                elif tp_idx == 1:  # TP2
                                    pos['remaining_size'] *= 0.67
                                else:  # TP3
                                    pos['exit_price'] = tp
                                    pos['exit_time'] = current_time
                                    pos['exit_reason'] = f'TP{tp_idx+1}'
                                    positions_to_close.append(pos)
                                    
                        elif pos['direction'] == 'short' and current_price <= tp:
                            if f'tp{tp_idx+1}_hit' not in pos:
                                pos[f'tp{tp_idx+1}_hit'] = True
                                if tp_idx == 2:
                                    pos['exit_price'] = tp
                                    pos['exit_time'] = current_time
                                    pos['exit_reason'] = f'TP{tp_idx+1}'
                                    positions_to_close.append(pos)
                                    
            # Close positions
            for pos in positions_to_close:
                self._close_position(pos)
                open_positions.remove(pos)
                
            # Generate new signals
            if len(open_positions) < max_concurrent:
                # Prepare tick data (simulate from OHLCV)
                tick_data = self._simulate_tick_data(current_data.tail(10))
                
                # Get signals
                signals = engine.generate_integrated_signals(
                    current_data,
                    tick_data,
                    current_price
                )
                
                # Take the best signal if available
                if signals and signals[0]['risk_reward'] >= 2.0:
                    signal = signals[0]
                    
                    # Calculate position size
                    risk_amount = self.balance * risk_per_trade
                    stop_distance = abs(signal['entry'] - signal['stop_loss'])
                    position_size = risk_amount / stop_distance
                    
                    # Create position
                    position = {
                        'entry_time': current_time,
                        'entry_price': signal['entry'],
                        'direction': signal['direction'],
                        'stop_loss': signal['stop_loss'],
                        'take_profits': signal['take_profits'],
                        'position_size': position_size,
                        'remaining_size': position_size,
                        'risk_amount': risk_amount,
                        'signal_strength': signal['signal_strength'],
                        'theories': signal['theories_aligned']
                    }
                    
                    open_positions.append(position)
                    
            # Update equity
            current_equity = self.balance
            for pos in open_positions:
                if pos['direction'] == 'long':
                    unrealized = (current_price - pos['entry_price']) * pos['remaining_size']
                else:
                    unrealized = (pos['entry_price'] - current_price) * pos['remaining_size']
                current_equity += unrealized
                
            self.equity_curve.append(current_equity)
            
        # Close any remaining positions
        for pos in open_positions:
            pos['exit_price'] = data.iloc[-1]['close']
            pos['exit_time'] = data.iloc[-1]['timestamp']
            pos['exit_reason'] = 'End of Data'
            self._close_position(pos)
            
        # Calculate statistics
        self._calculate_statistics()
        
        return self.statistics
        
    def _close_position(self, position: Dict):
        """Close a position and record the trade"""
        if position['direction'] == 'long':
            pnl = (position['exit_price'] - position['entry_price']) * position['remaining_size']
        else:
            pnl = (position['entry_price'] - position['exit_price']) * position['remaining_size']
            
        self.balance += pnl
        
        position['pnl'] = pnl
        position['pnl_percent'] = pnl / position['risk_amount']
        position['duration'] = position['exit_time'] - position['entry_time']
        
        self.trades.append(position)
        
    def _simulate_tick_data(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """Simulate tick data from OHLCV for hidden order detection"""
        tick_data = []
        
        for _, row in ohlcv_data.iterrows():
            # Simulate ticks within the candle
            num_ticks = np.random.randint(10, 50)
            
            for _ in range(num_ticks):
                tick = {
                    'timestamp': row['timestamp'],
                    'bid': np.random.uniform(row['low'], row['high']),
                    'ask': 0,  # Will be calculated
                    'volume': row['volume'] / num_ticks
                }
                tick['ask'] = tick['bid'] + np.random.uniform(0.1, 0.3)
                tick_data.append(tick)
                
        return pd.DataFrame(tick_data)
        
    def _calculate_statistics(self):
        """Calculate comprehensive backtest statistics"""
        if not self.trades:
            self.statistics = {'error': 'No trades executed'}
            return
            
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (running_max - equity_array) / running_max
        max_drawdown = np.max(drawdown)
        
        # Sharpe ratio (simplified)
        returns = np.diff(equity_array) / equity_array[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Theory-specific stats
        theory_performance = {}
        for theory in ['wyckoff', 'smc', 'maz', 'hidden_order']:
            theory_trades = [t for t in self.trades if theory in t['theories']]
            if theory_trades:
                theory_performance[theory] = {
                    'trades': len(theory_trades),
                    'win_rate': len([t for t in theory_trades if t['pnl'] > 0]) / len(theory_trades),
                    'avg_pnl': np.mean([t['pnl'] for t in theory_trades])
                }
                
        # Signal strength correlation
        strengths = [t['signal_strength'] for t in self.trades]
        pnls = [t['pnl_percent'] for t in self.trades]
        
        if len(strengths) > 1:
            correlation = np.corrcoef(strengths, pnls)[0, 1]
        else:
            correlation = 0
            
        self.statistics = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_return': (self.balance - self.initial_balance) / self.initial_balance,
            'final_balance': self.balance,
            'theory_performance': theory_performance,
            'signal_strength_correlation': correlation,
            'best_trade': max(self.trades, key=lambda x: x['pnl'])['pnl'],
            'worst_trade': min(self.trades, key=lambda x: x['pnl'])['pnl'],
            'avg_trade_duration': np.mean([t['duration'].total_seconds()/3600 for t in self.trades])
        }
        
    def generate_report(self, filename: str = 'backtest_report.json'):
        """Generate detailed backtest report"""
        report = {
            'summary': self.statistics,
            'trades': [
                {
                    'entry_time': t['entry_time'].isoformat() if isinstance(t['entry_time'], datetime) else str(t['entry_time']),
                    'exit_time': t['exit_time'].isoformat() if isinstance(t['exit_time'], datetime) else str(t['exit_time']),
                    'direction': t['direction'],
                    'entry_price': t['entry_price'],
                    'exit_price': t['exit_price'],
                    'pnl': t['pnl'],
                    'pnl_percent': t['pnl_percent'],
                    'theories': t['theories'],
                    'signal_strength': t['signal_strength'],
                    'exit_reason': t['exit_reason']
                }
                for t in self.trades
            ],
            'equity_curve': self.equity_curve,
            'parameters': {
                'initial_balance': self.initial_balance,
                'risk_per_trade': 0.01,
                'theories_used': ['wyckoff', 'smc', 'maz', 'hidden_orders']
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        return filename
        
    def plot_results(self):
        """Plot backtest results"""
        import matplotlib.pyplot as plt
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Equity curve
        ax1.plot(self.equity_curve, linewidth=2)
        ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Balance ($)')
        ax1.grid(True, alpha=0.3)
        
        # Drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (running_max - equity_array) / running_max * 100
        
        ax2.fill_between(range(len(drawdown)), drawdown, alpha=0.3, color='red')
        ax2.plot(drawdown, color='red', linewidth=2)
        ax2.set_title('Drawdown %', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Trade Number')
        ax2.set_ylabel('Drawdown %')
        ax2.grid(True, alpha=0.3)
        
        # Win/Loss distribution
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.trades if t['pnl'] <= 0]
        
        ax3.hist(wins, bins=20, alpha=0.6, color='green', label='Wins')
        ax3.hist(losses, bins=20, alpha=0.6, color='red', label='Losses')
        ax3.set_title('P&L Distribution', fontsize=14, fontweight='bold')
        ax3.set_xlabel('P&L ($)')
        ax3.set_ylabel('Frequency')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Theory performance
        if 'theory_performance' in self.statistics:
            theories = list(self.statistics['theory_performance'].keys())
            win_rates = [self.statistics['theory_performance'][t]['win_rate'] 
                        for t in theories]
            
            ax4.bar(theories, win_rates, color=['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24'])
            ax4.set_title('Win Rate by Theory', fontsize=14, fontweight='bold')
            ax4.set_ylabel('Win Rate')
            ax4.set_ylim(0, 1)
            ax4.grid(True, alpha=0.3, axis='y')
            
        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return 'backtest_results.png'

# Example usage
if __name__ == "__main__":
    print("Backtesting module created with methods:")
    print("- backtest_strategy()")
    print("- generate_report()")
    print("- plot_results()")
    print("\nExample usage:")
    print("backtester = TheoryBacktester(initial_balance=10000)")
    print("results = backtester.backtest_strategy(data, engine)")
    print("backtester.plot_results()")
