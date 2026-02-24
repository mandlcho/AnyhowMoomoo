"""
RSI (Relative Strength Index) calculator.

RSI is a momentum oscillator that measures the speed and magnitude of price changes.
It ranges from 0 to 100, with readings above 70 indicating overbought conditions
and readings below 30 indicating oversold conditions.

Uses Wilder's smoothing method (EMA with alpha = 1/period).
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Union
from loguru import logger

from data.models import OHLCV


class RSICalculator:
    """
    Calculate RSI using Wilder's smoothing method.
    
    RSI Formula:
        RS = Average Gain / Average Loss
        RSI = 100 - (100 / (1 + RS))
    
    Where:
        - Average Gain/Loss use Wilder's smoothing (EMA with alpha=1/period)
        - First average is simple average of first 'period' gains/losses
        - Subsequent values use: Prior Average × (period-1) + Current Value / period
    """
    
    def __init__(
        self,
        period: int = 14,
        overbought_threshold: float = 70.0,
        oversold_threshold: float = 30.0
    ):
        """
        Initialize RSI calculator.
        
        Args:
            period: Lookback period (default 14)
            overbought_threshold: RSI level considered overbought (default 70)
            oversold_threshold: RSI level considered oversold (default 30)
        """
        if period < 2:
            raise ValueError("RSI period must be at least 2")
        
        self.period = period
        self.overbought = overbought_threshold
        self.oversold = oversold_threshold
        
        logger.debug(
            f"RSICalculator initialized: period={period}, "
            f"overbought={overbought_threshold}, oversold={oversold_threshold}"
        )
    
    def calculate(self, bars: Union[List[OHLCV], pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate RSI for a series of bars.
        
        Args:
            bars: List of OHLCV bars or DataFrame with OHLCV columns (must be sorted by timestamp)
            
        Returns:
            DataFrame with columns:
                - timestamp: Bar timestamp
                - close: Closing price
                - price_change: Price change from previous bar
                - gain: Positive price changes (0 if negative)
                - loss: Negative price changes (0 if positive)
                - avg_gain: Wilder's smoothed average gain
                - avg_loss: Wilder's smoothed average loss
                - rs: Relative strength (avg_gain / avg_loss)
                - rsi: RSI value (0-100)
        """
        # Convert to DataFrame if needed
        if isinstance(bars, pd.DataFrame):
            df = bars[['timestamp', 'close']].copy()
        elif not bars:
            return pd.DataFrame()
        else:
            if len(bars) < self.period + 1:
                logger.warning(
                    f"Insufficient data for RSI calculation: "
                    f"need {self.period + 1} bars, got {len(bars)}"
                )
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {'timestamp': bar.timestamp, 'close': float(bar.close)}
                for bar in bars
            ])
        
        # Calculate price changes
        df['price_change'] = df['close'].diff()
        
        # Separate gains and losses
        df['gain'] = df['price_change'].apply(lambda x: x if x > 0 else 0)
        df['loss'] = df['price_change'].apply(lambda x: -x if x < 0 else 0)
        
        # Calculate Wilder's smoothed averages
        # First average: simple mean of first 'period' values
        # Subsequent: (prior_avg * (period - 1) + current_value) / period
        
        # Initialize with first period's simple average
        avg_gain = df['gain'].iloc[1:self.period + 1].mean()
        avg_loss = df['loss'].iloc[1:self.period + 1].mean()
        
        # Store results
        avg_gains = [np.nan] * self.period  # First 'period' values are NaN
        avg_losses = [np.nan] * self.period
        
        avg_gains.append(avg_gain)
        avg_losses.append(avg_loss)
        
        # Calculate subsequent smoothed averages
        for i in range(self.period + 1, len(df)):
            avg_gain = (avg_gain * (self.period - 1) + df['gain'].iloc[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + df['loss'].iloc[i]) / self.period
            
            avg_gains.append(avg_gain)
            avg_losses.append(avg_loss)
        
        df['avg_gain'] = avg_gains
        df['avg_loss'] = avg_losses
        
        # Calculate RS and RSI
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        # Handle division by zero (when avg_loss = 0, RSI = 100)
        df.loc[df['avg_loss'] == 0, 'rsi'] = 100.0
        
        logger.debug(f"Calculated RSI for {len(df)} bars (period={self.period})")
        return df
    
    def get_signal(self, rsi_value: float) -> str:
        """
        Get trading signal based on RSI value.
        
        Args:
            rsi_value: Current RSI value (0-100)
            
        Returns:
            Signal string:
                - 'extreme_oversold': RSI < 20
                - 'oversold': RSI < oversold_threshold (default 30)
                - 'neutral': RSI between oversold and overbought
                - 'overbought': RSI > overbought_threshold (default 70)
                - 'extreme_overbought': RSI > 80
        """
        if rsi_value < 20:
            return 'extreme_oversold'
        elif rsi_value < self.oversold:
            return 'oversold'
        elif rsi_value > 80:
            return 'extreme_overbought'
        elif rsi_value > self.overbought:
            return 'overbought'
        else:
            return 'neutral'
    
    def detect_divergence(
        self,
        rsi_df: pd.DataFrame,
        lookback: int = 5
    ) -> str:
        """
        Detect bullish/bearish divergence between price and RSI.
        
        Args:
            rsi_df: DataFrame from calculate() method
            lookback: Number of bars to look back for divergence
            
        Returns:
            'bullish_divergence', 'bearish_divergence', or 'none'
            
        Bullish divergence: Price makes lower low, but RSI makes higher low
        Bearish divergence: Price makes higher high, but RSI makes lower high
        """
        if len(rsi_df) < lookback * 2:
            return 'none'
        
        recent = rsi_df.tail(lookback * 2)
        
        # Get first half and second half
        first_half = recent.iloc[:lookback]
        second_half = recent.iloc[lookback:]
        
        # Find lows and highs
        first_price_low = first_half['close'].min()
        second_price_low = second_half['close'].min()
        
        first_rsi_low = first_half['rsi'].min()
        second_rsi_low = second_half['rsi'].min()
        
        first_price_high = first_half['close'].max()
        second_price_high = second_half['close'].max()
        
        first_rsi_high = first_half['rsi'].max()
        second_rsi_high = second_half['rsi'].max()
        
        # Check for bullish divergence (price lower low, RSI higher low)
        if second_price_low < first_price_low and second_rsi_low > first_rsi_low:
            return 'bullish_divergence'
        
        # Check for bearish divergence (price higher high, RSI lower high)
        if second_price_high > first_price_high and second_rsi_high < first_rsi_high:
            return 'bearish_divergence'
        
        return 'none'


def calculate_rsi_simple(bars: List[OHLCV], period: int = 14) -> pd.DataFrame:
    """
    Convenience function for simple RSI calculation.
    
    Args:
        bars: List of OHLCV bars
        period: RSI period (default 14)
        
    Returns:
        DataFrame with RSI values
    """
    calculator = RSICalculator(period=period)
    return calculator.calculate(bars)
