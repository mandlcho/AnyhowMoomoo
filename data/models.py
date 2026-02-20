"""
Core data transfer objects for the trading daemon.
All models use Pydantic for validation and serialization.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class MarketDataInterval(str, Enum):
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOUR_1 = "1hour"
    DAY_1 = "1day"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"  # For future use


# ============================================================================
# Market Data
# ============================================================================

class OHLCV(BaseModel):
    """Single OHLCV bar."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    interval: MarketDataInterval
    
    class Config:
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat(),
        }


class Tick(BaseModel):
    """Real-time tick data."""
    symbol: str
    timestamp: datetime
    price: Decimal
    size: int
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


class Quote(BaseModel):
    """Current quote snapshot."""
    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    last: Decimal
    volume: int
    vwap: Optional[Decimal] = None


# ============================================================================
# Account & Positions
# ============================================================================

class Position(BaseModel):
    """Open position."""
    symbol: str
    side: PositionSide
    quantity: Decimal  # Shares (can be fractional)
    avg_entry_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    
    # Risk management fields
    stop_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    entry_time: datetime
    planned_exit_time: Optional[datetime] = None  # For time-based stops


class AccountState(BaseModel):
    """Current account snapshot."""
    timestamp: datetime
    total_equity: Decimal
    cash: Decimal
    market_value: Decimal  # Total value of positions
    buying_power: Decimal
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    num_positions: int
    positions: List[Position] = Field(default_factory=list)


# ============================================================================
# Orders
# ============================================================================

class Order(BaseModel):
    """Order representation."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None  # For limit orders
    stop_price: Optional[Decimal] = None  # For stop orders
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    submit_time: datetime
    update_time: datetime
    
    # Internal tracking
    plan_id: Optional[str] = None  # Links to trade plan
    notes: Optional[str] = None


class OrderRequest(BaseModel):
    """Order request to send to broker."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK
    
    @validator('quantity')
    def quantity_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


# ============================================================================
# Indicators & Features
# ============================================================================

class IndicatorValues(BaseModel):
    """Computed technical indicators for a symbol."""
    symbol: str
    timestamp: datetime
    
    # Trend indicators
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    
    # Momentum
    rsi_14: Optional[Decimal] = None
    
    # Volatility
    atr_14: Optional[Decimal] = None
    bb_upper: Optional[Decimal] = None
    bb_middle: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None
    
    # Intraday
    vwap: Optional[Decimal] = None
    vwap_std_dev: Optional[Decimal] = None
    dist_from_vwap_pct: Optional[Decimal] = None  # (price - vwap) / vwap * 100


class MarketSnapshot(BaseModel):
    """
    Complete market snapshot for a symbol.
    This is what gets sent to Claude for analysis.
    """
    symbol: str
    timestamp: datetime
    current_price: Decimal
    
    # Recent price action
    daily_bars: List[OHLCV] = Field(default_factory=list)  # Last N days
    intraday_bars: List[OHLCV] = Field(default_factory=list)  # Today
    
    # Indicators
    indicators: IndicatorValues
    
    # Context
    avg_volume_20d: int
    sector: Optional[str] = None
    market_cap: Optional[Decimal] = None


# ============================================================================
# Trade Plans (Claude Interface)
# ============================================================================

class TradePlan(BaseModel):
    """
    Trade plan proposed by Claude (or generated by rules).
    This is the core structured output format.
    """
    plan_id: str  # UUID generated by daemon
    symbol: str
    direction: OrderSide
    
    # Rationale
    rationale: str  # Human-readable explanation
    timeframe: str  # e.g., "swing", "3-7 days", "intraday"
    expected_hold_days: Optional[int] = None
    
    # Price levels
    entry_price: Decimal  # Proposed entry (can be limit or market)
    stop_price: Decimal   # Hard stop loss
    target_prices: List[Decimal] = Field(default_factory=list)  # Can have multiple targets
    
    # Risk allocation
    allocation_risk_pct: Decimal  # % of account equity to risk
    target_notional: Optional[Decimal] = None  # Optional: specify dollar amount directly
    
    # Metadata
    created_at: datetime
    
    # Validation results (filled by daemon)
    validated: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    
    # Execution (filled after approval)
    approved: bool = False
    executed: bool = False
    order_ids: List[str] = Field(default_factory=list)


class TradePlanResponse(BaseModel):
    """
    Response from Claude containing one or more trade plans.
    """
    timestamp: datetime
    plans: List[TradePlan]
    commentary: Optional[str] = None  # General market commentary


# ============================================================================
# Configuration
# ============================================================================

class ExecutionMode(str, Enum):
    SEMI_AUTOMATIC = "SEMI_AUTOMATIC"
    AUTOMATIC = "AUTOMATIC"


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_risk_per_trade_pct: Decimal
    max_open_positions: int
    max_sector_exposure_pct: Decimal
    min_liquidity_avg_volume: int


class SizingConfig(BaseModel):
    """Position sizing configuration."""
    min_notional_per_trade: Decimal
    max_notional_per_trade: Decimal
    fractional_shares: bool
    min_rr_ratio: Decimal  # Minimum reward:risk ratio


class DaemonConfig(BaseModel):
    """Main daemon configuration."""
    execution_mode: ExecutionMode
    risk: RiskConfig
    sizing: SizingConfig
    opend_host: str = "127.0.0.1"
    opend_port: int = 11111
    paper_trading: bool = True
    cache_dir: str = "./data_cache"
    log_dir: str = "./logs"
