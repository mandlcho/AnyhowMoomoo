"""
Market snapshot aggregator for Claude integration.

Combines:
- Technical indicators (VWAP, RSI, ATR)
- Position sizing (Modified Kelly)
- Risk metrics
- Market conditions

Output: Clean JSON for Claude to analyze and generate trade plans.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, date
import pandas as pd
from loguru import logger

from features.vwap import VWAPCalculator
from features.rsi import RSICalculator
from features.atr import ATRCalculator
from position_sizing.calculator import PositionSizeCalculator, PositionSize


@dataclass
class TickerSnapshot:
    """
    Complete snapshot of a single ticker for Claude analysis.
    """
    # Basic info
    symbol: str
    timestamp: datetime
    current_price: float
    volume: int
    
    # Technical indicators
    vwap: float
    vwap_signal: str  # "oversold", "neutral", "overbought"
    vwap_distance_pct: float  # % from VWAP
    rsi: float
    rsi_signal: str  # "oversold", "neutral", "overbought"
    atr: float
    atr_pct: float  # ATR as % of price
    volatility_state: str  # "low", "normal", "high", "expanding", "contracting"
    
    # Position sizing (if strategy provided)
    recommended_shares: Optional[float] = None
    position_value: Optional[float] = None
    position_pct: Optional[float] = None
    stop_price: Optional[float] = None
    max_loss: Optional[float] = None
    risk_pct: Optional[float] = None
    
    # Additional context
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    entry_quality: Optional[str] = None  # "poor", "fair", "good", "excellent"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_claude_text(self) -> str:
        """
        Format for Claude consumption (human-readable).
        """
        lines = [
            f"== {self.symbol} ==",
            f"Price: ${self.current_price:.2f}",
            f"Volume: {self.volume:,}",
            "",
            "Technical Indicators:",
            f"  VWAP: ${self.vwap:.2f} ({self.vwap_signal}, {self.vwap_distance_pct:+.2%} from price)",
            f"  RSI: {self.rsi:.1f} ({self.rsi_signal})",
            f"  ATR: ${self.atr:.2f} ({self.atr_pct:.2%} volatility, {self.volatility_state})",
        ]
        
        if self.support_level or self.resistance_level:
            lines.append("")
            lines.append("Key Levels:")
            if self.support_level:
                lines.append(f"  Support: ${self.support_level:.2f}")
            if self.resistance_level:
                lines.append(f"  Resistance: ${self.resistance_level:.2f}")
        
        if self.recommended_shares is not None:
            lines.append("")
            lines.append("Position Sizing:")
            lines.append(f"  Shares: {self.recommended_shares:.2f}")
            lines.append(f"  Position: ${self.position_value:.2f} ({self.position_pct:.1%})")
            lines.append(f"  Stop: ${self.stop_price:.2f}")
            lines.append(f"  Risk: ${self.max_loss:.2f} ({self.risk_pct:.1%})")
        
        if self.entry_quality:
            lines.append("")
            lines.append(f"Entry Quality: {self.entry_quality.upper()}")
        
        return "\n".join(lines)


@dataclass
class MarketSnapshot:
    """
    Complete market snapshot for Claude decision-making.
    """
    timestamp: datetime
    market_date: date
    tickers: List[TickerSnapshot]
    market_condition: str  # "bullish", "neutral", "bearish"
    volatility_regime: str  # "low", "medium", "high"
    
    # Portfolio context
    account_balance: float
    available_cash: float
    current_positions: int
    total_exposure_pct: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "market_date": self.market_date.isoformat(),
            "tickers": [t.to_dict() for t in self.tickers],
            "market_condition": self.market_condition,
            "volatility_regime": self.volatility_regime,
            "account_balance": self.account_balance,
            "available_cash": self.available_cash,
            "current_positions": self.current_positions,
            "total_exposure_pct": self.total_exposure_pct,
        }
    
    def to_claude_text(self) -> str:
        """
        Format for Claude (comprehensive text summary).
        """
        lines = [
            "=" * 70,
            f"MARKET SNAPSHOT - {self.market_date}",
            "=" * 70,
            "",
            f"Market Condition: {self.market_condition.upper()}",
            f"Volatility Regime: {self.volatility_regime.upper()}",
            "",
            "Portfolio Status:",
            f"  Balance: ${self.account_balance:,.2f}",
            f"  Available: ${self.available_cash:,.2f}",
            f"  Positions: {self.current_positions}",
            f"  Exposure: {self.total_exposure_pct:.1%}",
            "",
            "=" * 70,
            f"TICKER ANALYSIS ({len(self.tickers)} symbols)",
            "=" * 70,
            "",
        ]
        
        for ticker in self.tickers:
            lines.append(ticker.to_claude_text())
            lines.append("")
        
        return "\n".join(lines)
    
    def get_top_opportunities(self, limit: int = 5) -> List[TickerSnapshot]:
        """
        Get top trading opportunities sorted by entry quality.
        """
        # Filter tickers with entry_quality
        qualified = [t for t in self.tickers if t.entry_quality]
        
        # Sort by quality (excellent > good > fair > poor)
        quality_order = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}
        sorted_tickers = sorted(
            qualified,
            key=lambda t: quality_order.get(t.entry_quality, 0),
            reverse=True
        )
        
        return sorted_tickers[:limit]


class MarketSnapshotBuilder:
    """
    Builds market snapshots by aggregating all technical analysis.
    """
    
    def __init__(
        self,
        vwap_calc: Optional[VWAPCalculator] = None,
        rsi_calc: Optional[RSICalculator] = None,
        atr_calc: Optional[ATRCalculator] = None,
        position_calc: Optional[PositionSizeCalculator] = None
    ):
        """
        Initialize snapshot builder with calculators.
        
        Args:
            vwap_calc: VWAP calculator (creates default if None)
            rsi_calc: RSI calculator (creates default if None)
            atr_calc: ATR calculator (creates default if None)
            position_calc: Position size calculator (creates default if None)
        """
        self.vwap = vwap_calc or VWAPCalculator()
        self.rsi = rsi_calc or RSICalculator()
        self.atr = atr_calc or ATRCalculator()
        self.position = position_calc or PositionSizeCalculator()
        
        logger.info("MarketSnapshotBuilder initialized")
    
    def build_ticker_snapshot(
        self,
        symbol: str,
        df: pd.DataFrame,
        account_balance: float,
        kelly_fraction: Optional[float] = None,
        risk_per_trade_pct: float = 1.0
    ) -> TickerSnapshot:
        """
        Build snapshot for a single ticker.
        
        Args:
            symbol: Ticker symbol
            df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            account_balance: Total account balance
            kelly_fraction: Kelly fraction for position sizing (optional)
            risk_per_trade_pct: Risk % per trade (default 1%)
            
        Returns:
            TickerSnapshot with all indicators and position sizing
        """
        # Get latest data
        latest = df.iloc[-1]
        current_price = latest['close']
        volume = latest['volume']
        timestamp = latest['timestamp']
        
        # Calculate indicators
        vwap_result = self.vwap.calculate(df)
        rsi_result = self.rsi.calculate(df)
        atr_result = self.atr.calculate(df)
        
        # Get latest values
        latest_vwap = vwap_result.iloc[-1]
        latest_rsi = rsi_result.iloc[-1]
        latest_atr = atr_result.iloc[-1]
        
        # Analyze VWAP
        vwap_signal = self.vwap.get_signal(
            current_price=current_price,
            vwap=latest_vwap['vwap'],
            upper_1std=latest_vwap['vwap_upper_1std'],
            lower_1std=latest_vwap['vwap_lower_1std'],
            upper_2std=latest_vwap.get('vwap_upper_2std'),
            lower_2std=latest_vwap.get('vwap_lower_2std')
        )
        vwap_distance = (current_price - latest_vwap['vwap']) / latest_vwap['vwap']
        
        # Analyze RSI
        rsi_signal = self.rsi.get_signal(latest_rsi['rsi'])
        
        # Analyze volatility (use simple classification)
        if latest_atr['atr_pct'] < 0.02:
            volatility_state = "low"
        elif latest_atr['atr_pct'] < 0.04:
            volatility_state = "normal"
        else:
            volatility_state = "high"
        
        # Calculate position sizing if Kelly fraction provided
        position_size = None
        if kelly_fraction is not None:
            position_size = self.position.calculate(
                account_balance=account_balance,
                current_price=current_price,
                atr=latest_atr['atr'],
                kelly_fraction=kelly_fraction,
                risk_per_trade_pct=risk_per_trade_pct
            )
        
        # Determine support/resistance from VWAP bands
        support = latest_vwap['vwap'] - latest_vwap['vwap_std'] * 2
        resistance = latest_vwap['vwap'] + latest_vwap['vwap_std'] * 2
        
        # Assess entry quality
        entry_quality = self._assess_entry_quality(
            vwap_signal=vwap_signal,
            rsi_signal=rsi_signal,
            volatility_state=volatility_state,
            vwap_distance=abs(vwap_distance)
        )
        
        snapshot = TickerSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            current_price=current_price,
            volume=volume,
            vwap=latest_vwap['vwap'],
            vwap_signal=vwap_signal,
            vwap_distance_pct=vwap_distance,
            rsi=latest_rsi['rsi'],
            rsi_signal=rsi_signal,
            atr=latest_atr['atr'],
            atr_pct=latest_atr['atr_pct'],
            volatility_state=volatility_state,
            support_level=support,
            resistance_level=resistance,
            entry_quality=entry_quality
        )
        
        # Add position sizing if calculated
        if position_size:
            snapshot.recommended_shares = position_size.shares
            snapshot.position_value = position_size.position_value
            snapshot.position_pct = position_size.position_fraction
            snapshot.stop_price = position_size.stop_price
            snapshot.max_loss = position_size.max_loss
            snapshot.risk_pct = position_size.risk_pct
        
        logger.debug(f"Built snapshot for {symbol}: {entry_quality} entry quality")
        
        return snapshot
    
    def build_market_snapshot(
        self,
        ticker_data: Dict[str, pd.DataFrame],
        account_balance: float,
        available_cash: float,
        current_positions: int,
        total_exposure_pct: float,
        kelly_fractions: Optional[Dict[str, float]] = None,
        risk_per_trade_pct: float = 1.0
    ) -> MarketSnapshot:
        """
        Build complete market snapshot for multiple tickers.
        
        Args:
            ticker_data: Dict mapping symbol -> DataFrame
            account_balance: Total account balance
            available_cash: Available cash for new positions
            current_positions: Number of current positions
            total_exposure_pct: Current portfolio exposure %
            kelly_fractions: Dict mapping symbol -> Kelly fraction (optional)
            risk_per_trade_pct: Risk % per trade
            
        Returns:
            MarketSnapshot with all tickers analyzed
        """
        kelly_fractions = kelly_fractions or {}
        
        # Build ticker snapshots
        snapshots = []
        for symbol, df in ticker_data.items():
            kelly = kelly_fractions.get(symbol)
            snapshot = self.build_ticker_snapshot(
                symbol=symbol,
                df=df,
                account_balance=account_balance,
                kelly_fraction=kelly,
                risk_per_trade_pct=risk_per_trade_pct
            )
            snapshots.append(snapshot)
        
        # Assess overall market condition
        market_condition = self._assess_market_condition(snapshots)
        volatility_regime = self._assess_volatility_regime(snapshots)
        
        market_snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            market_date=date.today(),
            tickers=snapshots,
            market_condition=market_condition,
            volatility_regime=volatility_regime,
            account_balance=account_balance,
            available_cash=available_cash,
            current_positions=current_positions,
            total_exposure_pct=total_exposure_pct
        )
        
        logger.info(
            f"Built market snapshot: {len(snapshots)} tickers, "
            f"{market_condition} market, {volatility_regime} volatility"
        )
        
        return market_snapshot
    
    def _assess_entry_quality(
        self,
        vwap_signal: str,
        rsi_signal: str,
        volatility_state: str,
        vwap_distance: float
    ) -> str:
        """
        Assess entry quality based on alignment of indicators.
        """
        score = 0
        
        # VWAP alignment (mean reversion bias)
        if vwap_signal == "oversold":
            score += 2  # Strong buy signal
        elif vwap_signal == "overbought":
            score -= 1  # Caution
        
        # RSI confirmation
        if rsi_signal == "oversold":
            score += 2
        elif rsi_signal == "overbought":
            score -= 1
        
        # Volatility preference (moderate is best)
        if volatility_state in ["normal", "low"]:
            score += 1
        elif volatility_state == "high":
            score -= 1
        
        # Distance from VWAP (closer is better for mean reversion)
        if vwap_distance < 0.02:  # Within 2%
            score += 1
        
        # Map score to quality
        if score >= 4:
            return "excellent"
        elif score >= 2:
            return "good"
        elif score >= 0:
            return "fair"
        else:
            return "poor"
    
    def _assess_market_condition(self, snapshots: List[TickerSnapshot]) -> str:
        """
        Assess overall market condition from ticker snapshots.
        """
        if not snapshots:
            return "neutral"
        
        # Count oversold vs overbought on VWAP
        oversold = sum(1 for s in snapshots if s.vwap_signal == "oversold")
        overbought = sum(1 for s in snapshots if s.vwap_signal == "overbought")
        
        oversold_pct = oversold / len(snapshots)
        overbought_pct = overbought / len(snapshots)
        
        if oversold_pct > 0.6:
            return "bearish"  # Many stocks oversold
        elif overbought_pct > 0.6:
            return "bullish"  # Many stocks overbought
        else:
            return "neutral"
    
    def _assess_volatility_regime(self, snapshots: List[TickerSnapshot]) -> str:
        """
        Assess overall volatility regime.
        """
        if not snapshots:
            return "medium"
        
        # Average ATR %
        avg_atr_pct = sum(s.atr_pct for s in snapshots) / len(snapshots)
        
        if avg_atr_pct < 0.02:  # < 2%
            return "low"
        elif avg_atr_pct < 0.04:  # 2-4%
            return "medium"
        else:  # > 4%
            return "high"
