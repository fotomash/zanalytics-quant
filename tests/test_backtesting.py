import pandas as pd
from backtesting.backtest_engine import BacktestEngine, example_ml_strategy


def test_run_backtest():
    data = pd.DataFrame({'close': [i for i in range(60)]})
    data.index = pd.date_range('2023-01-01', periods=60, freq='D')
    engine = BacktestEngine(initial_capital=1000)
    results = engine.run_backtest(data, example_ml_strategy)
    assert 'final_capital' in results
    assert isinstance(results['total_trades'], int)
