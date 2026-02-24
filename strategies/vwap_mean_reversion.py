"""
Simple VWAP mean-reversion strategy for demo purposes.

Strategy Logic:
- BUY when price is oversold (below VWAP lower 2σ band) AND RSI < 30
- SELL when price returns to VWAP OR RSI > 70
- Stop loss at 2x ATR below entry
"""

import pandas as pd
from typing import Dict, Optional
from loguru import logger

from features.vwap import VWAPCalculator
from features.rsi import RSICalculator
from features.atr import ATRCalculator
from backtest.engine import BacktestEngine, OrderSide
from position_sizing.calculator import PositionSizeCalculator


class VWAPMeanReversionStrategy:
    """
    Simple VWAP mean-reversion strategy.
    """
    
    def __init__(
        self,
        vwap_calc: Optional[VWAPCalculator] = None,
        rsi_calc: Optional[RSICalculator] = None,
        atr_calc: Optional[ATRCalculator] = None,
        position_calc: Optional[PositionSizeCalculator] = None,
        kelly_fraction: float = 0.10,  # Conservative 10%
        risk_per_trade_pct: float = 1.0
    ):
        """
        Initialize strategy.
        
        Args:
            vwap_calc: VWAP calculator
            rsi_calc: RSI calculator
            atr_calc: ATR calculator
            position_calc: Position size calculator
            kelly_fraction: Kelly fraction for position sizing
            risk_per_trade_pct: Risk % per trade
        """
        self.vwap = vwap_calc or VWAPCalculator()
        self.rsi = rsi_calc or RSICalculator(period=14, overbought_threshold=70, oversold_threshold=30)
        self.atr = atr_calc or ATRCalculator(period=14)
        self.position = position_calc or PositionSizeCalculator()
        
        self.kelly_fraction = kelly_fraction
        self.risk_per_trade_pct = risk_per_trade_pct
        
        logger.info("VWAPMeanReversionStrategy initialized")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals for a DataFrame.
        
        Args:
            df: DataFrame with OHLCV columns
            
        Returns:
            DataFrame with added columns: signal, vwap, rsi, atr
        """
        # Calculate indicators
        vwap_df = self.vwap.calculate(df)
        rsi_df = self.rsi.calculate(df)
        atr_df = self.atr.calculate(df)
        
        # Merge indicators
        result = df.copy()
        result['vwap'] = vwap_df['vwap']
        result['vwap_lower_2std'] = vwap_df['vwap_lower_2std']
        result['vwap_upper_2std'] = vwap_df['vwap_upper_2std']
        result['rsi'] = rsi_df['rsi']
        result['atr'] = atr_df['atr']
        
        # Generate signals
        result['signal'] = 'hold'
        
        # BUY: Price < VWAP lower 2σ AND RSI < 30
        buy_condition = (
            (result['close'] < result['vwap_lower_2std']) &
            (result['rsi'] < 30)
        )
        result.loc[buy_condition, 'signal'] = 'buy'
        
        # SELL: Price > VWAP OR RSI > 70
        sell_condition = (
            (result['close'] > result['vwap']) |
            (result['rsi'] > 70)
        )
        result.loc[sell_condition, 'signal'] = 'sell'
        
        return result
    
    def backtest(
        self,
        symbol: str,
        df: pd.DataFrame,
        engine: BacktestEngine
    ) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            symbol: Stock symbol
            df: Historical OHLCV data
            engine: Backtest engine
            
        Returns:
            Dict with results
        """
        # Generate signals
        signals_df = self.generate_signals(df)
        
        # Track position
        in_position = False
        entry_price = None
        stop_price = None
        
        # Iterate through bars
        for i, row in signals_df.iterrows():
            timestamp = row['timestamp']
            close = row['close']
            high = row['high']
            low = row['low']
            open_price = row['open']
            volume = row['volume']
            vwap = row['vwap']
            atr = row['atr']
            signal = row['signal']
            
            # Process bar in engine (fills pending orders)
            engine.process_bar(
                symbol=symbol,
                timestamp=timestamp,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                vwap=vwap
            )
            
            # Check stop loss if in position
            if in_position and stop_price is not None:
                if low <= stop_price:
                    # Stop hit - submit sell order
                    shares = engine.positions.get(symbol).shares if symbol in engine.positions else 0
                    if shares > 0:
                        engine.submit_order(
                            symbol=symbol,
                            side=OrderSide.SELL,
                            shares=shares,
                            timestamp=timestamp
                        )
                        in_position = False
                        logger.debug(f"Stop loss hit @ ${stop_price:.2f}")
                        continue
            
            # Entry signal
            if not in_position and signal == 'buy':
                # Calculate position size
                position_size = self.position.calculate(
                    account_balance=engine.equity,
                    current_price=close,
                    atr=atr,
                    kelly_fraction=self.kelly_fraction,
                    risk_per_trade_pct=self.risk_per_trade_pct
                )
                
                if position_size.shares > 0:
                    # Submit buy order
                    engine.submit_order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        shares=position_size.shares,
                        timestamp=timestamp
                    )
                    
                    in_position = True
                    entry_price = close
                    stop_price = close - (atr * 2)  # 2 ATR stop
                    
                    logger.debug(
                        f"BUY signal @ ${close:.2f}, "
                        f"shares={position_size.shares:.2f}, "
                        f"stop=${stop_price:.2f}"
                    )
            
            # Exit signal
            elif in_position and signal == 'sell':
                shares = engine.positions.get(symbol).shares if symbol in engine.positions else 0
                if shares > 0:
                    engine.submit_order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        shares=shares,
                        timestamp=timestamp
                    )
                    in_position = False
                    logger.debug(f"SELL signal @ ${close:.2f}")
        
        # Close any remaining positions at end
        if symbol in engine.positions:
            final_row = signals_df.iloc[-1]
            engine.submit_order(
                symbol=symbol,
                side=OrderSide.SELL,
                shares=engine.positions[symbol].shares,
                timestamp=final_row['timestamp']
            )
            # Process final bar to fill the order
            engine.process_bar(
                symbol=symbol,
                timestamp=final_row['timestamp'],
                open_price=final_row['open'],
                high=final_row['high'],
                low=final_row['low'],
                close=final_row['close'],
                volume=final_row['volume'],
                vwap=final_row['vwap']
            )
        
        # Calculate metrics
        metrics = engine.calculate_metrics()
        
        return {
            'metrics': metrics,
            'trades': engine.get_trades_df(),
            'equity_curve': engine.get_equity_curve_df()
        }
