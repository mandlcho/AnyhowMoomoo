"""
ATR (Average True Range) calculator.

ATR measures market volatility by calculating the average of true ranges over a period.
It's particularly useful for:
- Setting stop-loss distances
- Position sizing based on volatility
- Identifying volatility expansion/contraction

True Range handles overnight gaps better than simple High-Low range.
"""

import pandas as pd
import numpy as np
from typing import List, Union
from loguru import logger

from data.models import OHLCV


class ATRCalculator:
    """
    Calculate ATR (Average True Range) with optional normalization.
    
    True Range Formula:
        TR = max(High - Low, abs(High - Previous Close), abs(Low - Previous Close))
    
    ATR Formula:
        ATR = EMA(TR, period)  # Exponential Moving Average of True Range
        
    Normalized ATR:
        ATR% = (ATR / Current Price) × 100
    """
    
    def __init__(
        self,
        period: int = 14,
        normalize: bool = True,
        stop_multiplier: float = 2.0
    ):
        """
        Initialize ATR calculator.
        
        Args:
            period: Lookback period for averaging (default 14)
            normalize: Return ATR as % of current price (default True)
            stop_multiplier: Multiplier for stop-loss distance suggestions (default 2.0)
        """
        if period < 1:
            raise ValueError("ATR period must be at least 1")
        
        self.period = period
        self.normalize = normalize
        self.stop_multiplier = stop_multiplier
        
        logger.debug(
            f"ATRCalculator initialized: period={period}, "
            f"normalize={normalize}, stop_multiplier={stop_multiplier}"
        )
    
    def calculate(self, bars: Union[List[OHLCV], pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate ATR for a series of bars.
        
        Args:
            bars: List of OHLCV bars or DataFrame with OHLCV columns (must be sorted by timestamp)
            
        Returns:
            DataFrame with columns:
                - timestamp: Bar timestamp
                - high: High price
                - low: Low price
                - close: Close price
                - prev_close: Previous close price
                - tr: True Range
                - atr: Average True Range
                - atr_pct: ATR as % of price (if normalize=True)
                - stop_distance: Suggested stop distance (atr × stop_multiplier)
        """
        # Convert to DataFrame if needed
        if isinstance(bars, pd.DataFrame):
            df = bars[['timestamp', 'high', 'low', 'close']].copy()
        elif not bars:
            return pd.DataFrame()
        else:
            if len(bars) < self.period:
                logger.warning(
                    f"Insufficient data for ATR calculation: "
                    f"need {self.period} bars, got {len(bars)}"
                )
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    'timestamp': bar.timestamp,
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                }
                for bar in bars
            ])
        
        # Calculate previous close
        df['prev_close'] = df['close'].shift(1)
        
        # Calculate True Range
        # TR = max(H-L, abs(H-PC), abs(L-PC))
        df['hl'] = df['high'] - df['low']
        df['hpc'] = abs(df['high'] - df['prev_close'])
        df['lpc'] = abs(df['low'] - df['prev_close'])
        
        df['tr'] = df[['hl', 'hpc', 'lpc']].max(axis=1)
        
        # Calculate ATR using EMA (Wilder's smoothing)
        # First ATR = simple average of first 'period' TRs
        # Subsequent: ATR = (Prior ATR × (period - 1) + Current TR) / period
        
        # Initialize with first period's simple average
        first_atr = df['tr'].iloc[1:self.period + 1].mean()
        
        # Store results
        atr_values = [np.nan] * self.period  # First 'period' values are NaN
        atr_values.append(first_atr)
        
        # Calculate subsequent ATRs
        for i in range(self.period + 1, len(df)):
            atr = (atr_values[-1] * (self.period - 1) + df['tr'].iloc[i]) / self.period
            atr_values.append(atr)
        
        df['atr'] = atr_values
        
        # Normalize ATR to percentage of price
        if self.normalize:
            df['atr_pct'] = (df['atr'] / df['close']) * 100
        
        # Calculate suggested stop distance
        df['stop_distance'] = df['atr'] * self.stop_multiplier
        
        # Clean up intermediate columns
        df.drop(columns=['hl', 'hpc', 'lpc'], inplace=True)
        
        logger.debug(f"Calculated ATR for {len(df)} bars (period={self.period})")
        return df
    
    def suggest_stop_distance(self, atr: float) -> float:
        """
        Suggest stop-loss distance based on ATR.
        
        Args:
            atr: Current ATR value
            
        Returns:
            Suggested stop distance (ATR × stop_multiplier)
            
        Example:
            If ATR = $2.50 and stop_multiplier = 2.0:
            Stop distance = $5.00
        """
        return atr * self.stop_multiplier
    
    def calculate_position_size(
        self,
        account_balance: float,
        risk_per_trade_pct: float,
        current_price: float,
        atr: float
    ) -> float:
        """
        Calculate position size based on ATR and risk percentage.
        
        Args:
            account_balance: Total account balance
            risk_per_trade_pct: Maximum % of account to risk per trade (e.g., 1.0 for 1%)
            current_price: Current stock price
            atr: Current ATR value
            
        Returns:
            Number of shares to buy
            
        Example:
            Account: $10,000
            Risk: 1% = $100
            Price: $150
            ATR: $3.00
            Stop distance: 2 × ATR = $6.00
            Position size: $100 / $6.00 = 16.67 shares
        """
        max_loss = account_balance * (risk_per_trade_pct / 100)
        stop_distance = self.suggest_stop_distance(atr)
        
        # Shares = Max Loss / Stop Distance
        shares = max_loss / stop_distance
        
        return shares
    
    def get_volatility_signal(self, atr_df: pd.DataFrame, lookback: int = 20) -> str:
        """
        Detect volatility expansion or contraction.
        
        Args:
            atr_df: DataFrame from calculate() method
            lookback: Number of bars to compare against
            
        Returns:
            'expanding', 'contracting', or 'normal'
            
        Expanding: Current ATR > 1.5 × average ATR over lookback
        Contracting: Current ATR < 0.67 × average ATR over lookback
        """
        if len(atr_df) < lookback + 1:
            return 'normal'
        
        recent = atr_df.tail(lookback + 1)
        current_atr = recent['atr'].iloc[-1]
        avg_atr = recent['atr'].iloc[:-1].mean()
        
        if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
            return 'normal'
        
        ratio = current_atr / avg_atr
        
        if ratio > 1.5:
            return 'expanding'
        elif ratio < 0.67:
            return 'contracting'
        else:
            return 'normal'


def calculate_atr_simple(
    bars: List[OHLCV],
    period: int = 14,
    normalize: bool = True
) -> pd.DataFrame:
    """
    Convenience function for simple ATR calculation.
    
    Args:
        bars: List of OHLCV bars
        period: ATR period (default 14)
        normalize: Return ATR as % of price (default True)
        
    Returns:
        DataFrame with ATR values
    """
    calculator = ATRCalculator(period=period, normalize=normalize)
    return calculator.calculate(bars)
