
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import json


@dataclass
class Trade:
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    size: float
    direction: str
    pnl: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0

    def calculate_pnl(self) -> float:
        if self.exit_price is None:
            return 0.0
        if self.direction == 'long':
            gross_pnl = (self.exit_price - self.entry_price) * self.size
        else:
            gross_pnl = (self.entry_price - self.exit_price) * self.size
        self.pnl = gross_pnl - self.commission - self.slippage
        return self.pnl


class BacktestEngine:
    """Comprehensive backtesting engine for ML+Risk strategies"""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: List[Trade] = []
        self.positions: Dict[str, Trade] = {}
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.commission_rate = 0.001
        self.slippage_rate = 0.0005
        logging.info(f"BacktestEngine initialized with ${initial_capital:,.2f}")

    def run_backtest(self, data: pd.DataFrame, strategy_func: callable,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict:
        logging.info("Starting backtest...")
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        self.current_capital = self.initial_capital
        self.trades = []
        self.positions = {}
        self.equity_curve = []
        for i, (timestamp, row) in enumerate(data.iterrows()):
            signals = strategy_func(data.iloc[:i+1])
            for signal in signals:
                self._process_signal(signal, row, timestamp)
            current_equity = self._calculate_current_equity(row)
            self.equity_curve.append((timestamp, current_equity))
            if i % 1000 == 0:
                logging.info(f"Processed {i} bars, Current Equity: ${current_equity:,.2f}")
        self._close_all_positions(data.iloc[-1], data.index[-1])
        self.performance_metrics = self._calculate_performance_metrics()
        logging.info("Backtest completed")
        return self.performance_metrics

    def _process_signal(self, signal: Dict, market_data: pd.Series, timestamp: datetime):
        symbol = signal.get('symbol', 'DEFAULT')
        action = signal.get('action', 'HOLD')
        position_size = signal.get('position_size', 0.1)
        current_price = market_data['close']
        if action == 'BUY' and symbol not in self.positions:
            self._open_position(symbol, 'long', current_price, position_size, timestamp)
        elif action == 'SELL' and symbol not in self.positions:
            self._open_position(symbol, 'short', current_price, position_size, timestamp)
        elif action == 'HOLD' and symbol in self.positions:
            self._close_position(symbol, current_price, timestamp)

    def _open_position(self, symbol: str, direction: str, price: float,
                        position_size: float, timestamp: datetime):
        position_value = self.current_capital * position_size
        shares = position_value / price
        commission = position_value * self.commission_rate
        slippage = position_value * self.slippage_rate
        adjusted_price = price * (1 + self.slippage_rate) if direction == 'long' else price * (1 - self.slippage_rate)
        trade = Trade(symbol, timestamp, None, adjusted_price, None, shares, direction,
                      commission=commission, slippage=slippage)
        self.positions[symbol] = trade
        self.current_capital -= (commission + slippage)
        logging.debug(f"Opened {direction} position: {symbol} @ ${adjusted_price:.2f}")

    def _close_position(self, symbol: str, price: float, timestamp: datetime):
        if symbol not in self.positions:
            return
        trade = self.positions[symbol]
        position_value = abs(trade.size * price)
        exit_commission = position_value * self.commission_rate
        exit_slippage = position_value * self.slippage_rate
        adjusted_price = price * (1 - self.slippage_rate) if trade.direction == 'long' else price * (1 + self.slippage_rate)
        trade.exit_time = timestamp
        trade.exit_price = adjusted_price
        trade.commission += exit_commission
        trade.slippage += exit_slippage
        pnl = trade.calculate_pnl()
        self.current_capital += pnl
        self.trades.append(trade)
        del self.positions[symbol]
        logging.debug(f"Closed position: {symbol} @ ${adjusted_price:.2f}, P&L: ${pnl:.2f}")

    def _close_all_positions(self, market_data: pd.Series, timestamp: datetime):
        for symbol in list(self.positions.keys()):
            self._close_position(symbol, market_data['close'], timestamp)

    def _calculate_current_equity(self, market_data: pd.Series) -> float:
        equity = self.current_capital
        for symbol, trade in self.positions.items():
            current_price = market_data['close']
            if trade.direction == 'long':
                unrealized = (current_price - trade.entry_price) * trade.size
            else:
                unrealized = (trade.entry_price - current_price) * trade.size
            equity += unrealized
        return equity

    def _calculate_performance_metrics(self) -> Dict:
        if not self.trades:
            return {'error': 'No trades executed'}
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        total_pnl = sum(t.pnl for t in self.trades)
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')
        equity_returns = equity_df['equity'].pct_change().dropna()
        volatility = equity_returns.std() * np.sqrt(252)
        sharpe_ratio = (equity_returns.mean() * 252) / volatility if volatility > 0 else 0
        running_max = equity_df['equity'].cummax()
        drawdown = (equity_df['equity'] - running_max) / running_max
        max_drawdown = drawdown.min()
        calmar_ratio = (total_return * 252) / abs(max_drawdown) if max_drawdown != 0 else 0
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'final_capital': self.current_capital,
            'equity_curve': equity_df.to_dict('records'),
        }

    def generate_trade_report(self) -> pd.DataFrame:
        trade_data = []
        for trade in self.trades:
            trade_data.append({
                'symbol': trade.symbol,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'direction': trade.direction,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'size': trade.size,
                'pnl': trade.pnl,
                'commission': trade.commission,
                'slippage': trade.slippage,
                'hold_time': (trade.exit_time - trade.entry_time).total_seconds() / 3600 if trade.exit_time else 0,
            })
        return pd.DataFrame(trade_data)

    def save_results(self, filepath: str):
        results = {
            'performance_metrics': self.performance_metrics,
            'trades': [
                {
                    'symbol': t.symbol,
                    'entry_time': t.entry_time.isoformat(),
                    'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'size': t.size,
                    'direction': t.direction,
                    'pnl': t.pnl,
                    'commission': t.commission,
                    'slippage': t.slippage,
                }
                for t in self.trades
            ],
            'equity_curve': [{'timestamp': ts.isoformat(), 'equity': eq} for ts, eq in self.equity_curve],
        }
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Backtest results saved to {filepath}")


def example_ml_strategy(data: pd.DataFrame) -> List[Dict]:
    if len(data) < 50:
        return []
    signals = []
    short_ma = data['close'].rolling(10).mean().iloc[-1]
    long_ma = data['close'].rolling(30).mean().iloc[-1]
    ml_confidence = 0.7 if short_ma > long_ma else 0.3
    if short_ma > long_ma and ml_confidence > 0.6:
        signals.append({'symbol': 'DEFAULT', 'action': 'BUY', 'confidence': ml_confidence, 'position_size': 0.1})
    elif short_ma < long_ma and ml_confidence < 0.4:
        signals.append({'symbol': 'DEFAULT', 'action': 'SELL', 'confidence': 1 - ml_confidence, 'position_size': 0.1})
    return signals


if __name__ == "__main__":
    backtest = BacktestEngine()
    print("BacktestEngine initialized")
