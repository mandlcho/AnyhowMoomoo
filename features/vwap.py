"""
VWAP (Volume-Weighted Average Price) calculator with standard deviation bands.

VWAP is the average price weighted by volume, typically calculated from market open.
It's used to identify entry/exit points relative to the "fair value" of a security.

Standard deviation bands show volatility zones around VWAP.
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import List, Tuple, Optional, Union
from loguru import logger

from data.models import OHLCV


class VWAPCalculator:
    """
    Calculate VWAP with standard deviation bands.
    
    VWAP Formula:
        VWAP = Σ(Price × Volume) / Σ(Volume)
        where Price = (High + Low + Close) / 3 (typical price)
    
    Standard Deviation Bands:
        Upper Band (1σ) = VWAP + (1 × StdDev)
        Lower Band (1σ) = VWAP - (1 × StdDev)
        Upper Band (2σ) = VWAP + (2 × StdDev)
        Lower Band (2σ) = VWAP - (2 × StdDev)
    """
    
    def __init__(self, reset_time: str = "09:30", std_bands: List[float] = [1.0, 2.0]):
        """
        Initialize VWAP calculator.
        
        Args:
            reset_time: Market open time in HH:MM format (Eastern Time)
            std_bands: Standard deviation multipliers for bands (e.g., [1.0, 2.0])
        """
        self.reset_time = reset_time
        self.std_bands = sorted(std_bands)  # Ensure ascending order
        
        # Parse reset time
        hour, minute = map(int, reset_time.split(':'))
        self.reset_time_obj = time(hour, minute)
        
        logger.debug(f"VWAPCalculator initialized: reset_time={reset_time}, bands={std_bands}")
    
    def calculate(
        self,
        bars: Union[List[OHLCV], pd.DataFrame],
        use_typical_price: bool = True
    ) -> pd.DataFrame:
        """
        Calculate VWAP and standard deviation bands.
        
        Args:
            bars: List of OHLCV bars or DataFrame with OHLCV columns (must be sorted by timestamp)
            use_typical_price: Use (H+L+C)/3 instead of just Close
            
        Returns:
            DataFrame with columns:
                - timestamp: Bar timestamp
                - price: Input price used
                - volume: Bar volume
                - vwap: Volume-weighted average price
                - vwap_std: Standard deviation
                - vwap_upper_1std, vwap_lower_1std: 1σ bands
                - vwap_upper_2std, vwap_lower_2std: 2σ bands (if configured)
        """
        # Convert to DataFrame if needed
        if isinstance(bars, pd.DataFrame):
            df = bars.copy()
        elif not bars:
            return pd.DataFrame()
        else:
            # Convert list of OHLCV to DataFrame
            df = pd.DataFrame([
                {
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': bar.volume
                }
                for bar in bars
            ])
        
        # Calculate price (typical price or close)
        if use_typical_price:
            df['price'] = (df['high'] + df['low'] + df['close']) / 3.0
        else:
            df['price'] = df['close']
        
        # Detect session resets (market open times)
        df['time'] = df['timestamp'].dt.time
        df['is_reset'] = df['time'] == self.reset_time_obj
        df['session'] = df['is_reset'].cumsum()
        
        # Count sessions before processing
        num_sessions = df['session'].max()
        
        # Group by session to calculate cumulative VWAP
        def calc_session_vwap(group):
            """Calculate VWAP for a single session"""
            # Cumulative price * volume
            group = group.copy()
            group['cumul_pv'] = (group['price'] * group['volume']).cumsum()
            # Cumulative volume
            group['cumul_vol'] = group['volume'].cumsum()
            # VWAP = cumulative (price * volume) / cumulative volume
            group['vwap'] = group['cumul_pv'] / group['cumul_vol']
            
            # Calculate standard deviation
            # StdDev = sqrt(Σ(volume × (price - vwap)²) / Σ(volume))
            group['price_diff_sq'] = (group['price'] - group['vwap']) ** 2
            group['cumul_var'] = (group['volume'] * group['price_diff_sq']).cumsum()
            group['vwap_variance'] = group['cumul_var'] / group['cumul_vol']
            group['vwap_std'] = np.sqrt(group['vwap_variance'])
            
            return group
        
        # Apply VWAP calculation per session
        df = df.groupby('session', group_keys=False).apply(calc_session_vwap, include_groups=False)
        
        # Calculate standard deviation bands
        for multiplier in self.std_bands:
            df[f'vwap_upper_{int(multiplier)}std'] = df['vwap'] + (multiplier * df['vwap_std'])
            df[f'vwap_lower_{int(multiplier)}std'] = df['vwap'] - (multiplier * df['vwap_std'])
        
        # Clean up intermediate columns
        result_columns = ['timestamp', 'price', 'volume', 'vwap', 'vwap_std']
        for multiplier in self.std_bands:
            result_columns.append(f'vwap_upper_{int(multiplier)}std')
            result_columns.append(f'vwap_lower_{int(multiplier)}std')
        
        result = df[result_columns].copy()
        
        logger.debug(f"Calculated VWAP for {len(result)} bars across {num_sessions} sessions")
        return result
    
    def get_signal(
        self,
        current_price: float,
        vwap: float,
        upper_1std: float,
        lower_1std: float,
        upper_2std: Optional[float] = None,
        lower_2std: Optional[float] = None
    ) -> str:
        """
        Get trading signal based on price position relative to VWAP bands.
        
        Args:
            current_price: Current price
            vwap: VWAP value
            upper_1std: Upper 1σ band
            lower_1std: Lower 1σ band
            upper_2std: Upper 2σ band (optional)
            lower_2std: Lower 2σ band (optional)
            
        Returns:
            Signal string:
                - 'extreme_overbought': Price > 2σ above VWAP
                - 'overbought': Price between 1σ and 2σ above VWAP
                - 'above_vwap': Price slightly above VWAP
                - 'at_vwap': Price near VWAP (±0.1%)
                - 'below_vwap': Price slightly below VWAP
                - 'oversold': Price between 1σ and 2σ below VWAP
                - 'extreme_oversold': Price > 2σ below VWAP
        """
        # Calculate distance from VWAP as percentage
        vwap_distance_pct = ((current_price - vwap) / vwap) * 100
        
        # At VWAP (within ±0.1%)
        if abs(vwap_distance_pct) < 0.1:
            return 'at_vwap'
        
        # Check against 2σ bands if available
        if upper_2std and lower_2std:
            if current_price >= upper_2std:
                return 'extreme_overbought'
            elif current_price <= lower_2std:
                return 'extreme_oversold'
        
        # Check against 1σ bands
        if current_price >= upper_1std:
            return 'overbought'
        elif current_price <= lower_1std:
            return 'oversold'
        
        # Between VWAP and 1σ bands
        if current_price > vwap:
            return 'above_vwap'
        else:
            return 'below_vwap'
    
    def get_entry_exit_levels(
        self,
        vwap_df: pd.DataFrame,
        strategy: str = 'mean_reversion'
    ) -> Tuple[float, float, float]:
        """
        Calculate suggested entry, target, and stop levels based on VWAP.
        
        Args:
            vwap_df: DataFrame from calculate() method
            strategy: Trading strategy ('mean_reversion' or 'trend_following')
            
        Returns:
            Tuple of (entry_price, target_price, stop_price)
            
        Example (mean reversion):
            - Entry: Price touches lower 1σ band
            - Target: VWAP
            - Stop: Lower 2σ band
        """
        if vwap_df.empty:
            raise ValueError("VWAP DataFrame is empty")
        
        latest = vwap_df.iloc[-1]
        vwap = latest['vwap']
        
        if strategy == 'mean_reversion':
            # Buy when oversold, sell at VWAP
            entry = latest.get('vwap_lower_1std', vwap * 0.99)
            target = vwap
            stop = latest.get('vwap_lower_2std', vwap * 0.98)
            
        elif strategy == 'trend_following':
            # Buy breakout above VWAP
            entry = vwap
            target = latest.get('vwap_upper_1std', vwap * 1.01)
            stop = latest.get('vwap_lower_1std', vwap * 0.99)
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return (entry, target, stop)


def calculate_vwap_simple(bars: List[OHLCV]) -> pd.DataFrame:
    """
    Convenience function for simple VWAP calculation with default settings.
    
    Args:
        bars: List of OHLCV bars
        
    Returns:
        DataFrame with VWAP and standard deviation bands
    """
    calculator = VWAPCalculator()
    return calculator.calculate(bars)
