"""Quick backtest on a more volatile stock."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
import pandas as pd
from data.storage import DataStore
from data.fetcher import HybridDataFetcher, YFinanceDataSource, RateLimiter
from backtest.engine import BacktestEngine, BacktestConfig
from strategies.vwap_mean_reversion import VWAPMeanReversionStrategy

async def main():
    # Try Intel - more volatile
    symbol = sys.argv[1] if len(sys.argv) > 1 else "INTC"
    
    store = DataStore()
    limiter = RateLimiter(60)
    source = YFinanceDataSource(limiter)
    fetcher = HybridDataFetcher(fallback=source, storage=store)
    
    end = datetime.now()
    start = end - timedelta(days=180)
    
    print(f"Fetching {symbol}...")
    bars = await fetcher.fetch_daily_bars(symbol, start, end)
    
    if not bars:
        print("No data!")
        return
    
    df = pd.DataFrame([{
        'timestamp': b.timestamp,
        'open': float(b.open),
        'high': float(b.high),
        'low': float(b.low),
        'close': float(b.close),
        'volume': b.volume,
    } for b in bars])
    
    print(f"Got {len(bars)} bars: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")
    
    strategy = VWAPMeanReversionStrategy(kelly_fraction=0.10, risk_per_trade_pct=1.0)
    config = BacktestConfig(initial_capital=10000.0, use_vwap_fills=True)
    engine = BacktestEngine(config)
    
    signals = strategy.generate_signals(df)
    buys = (signals['signal'] == 'buy').sum()
    sells = (signals['signal'] == 'sell').sum()
    print(f"Signals: {buys} BUY, {sells} SELL")
    
    if buys == 0:
        print("❌ No buy signals - strategy too strict or market not oversold enough")
        print(f"Latest RSI: {signals['rsi'].iloc[-1]:.1f}")
        print(f"Price vs VWAP-2σ: ${signals['close'].iloc[-1]:.2f} vs ${signals['vwap_lower_2std'].iloc[-1]:.2f}")
        return
    
    print("Running backtest...")
    results = strategy.backtest(symbol, signals, engine)
    metrics = results['metrics']
    
    print(f"\nResults:")
    print(f"  Trades: {metrics.total_trades}")
    print(f"  Win Rate: {metrics.win_rate:.1%}")
    print(f"  Total Return: {metrics.total_return_pct:.1%}")
    print(f"  Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"  Max DD: {metrics.max_drawdown_pct:.1%}")

asyncio.run(main())
