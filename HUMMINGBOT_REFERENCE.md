# Hummingbot Reference Guide for AnyhowMoomoo

This document extracts key architectural patterns and code examples from [Hummingbot](https://github.com/hummingbot/hummingbot) (17.3k stars, production-grade trading bot framework) that are relevant to building AnyhowMoomoo.

**Purpose:** Reference material for Phase 2-5 implementation. Study these patterns when building each phase.

**Last Updated:** February 2026

---

## Table of Contents

- [Why Hummingbot?](#why-hummingbot)
- [Phase 2: Connector Architecture](#phase-2-connector-architecture)
- [Phase 2: Data Models & Types](#phase-2-data-models--types)
- [Phase 3: Strategy Framework](#phase-3-strategy-framework)
- [Phase 4: Order Tracking & Lifecycle](#phase-4-order-tracking--lifecycle)
- [Phase 4: Risk Management & Position Sizing](#phase-4-risk-management--position-sizing)
- [Phase 4: Event System](#phase-4-event-system)
- [Configuration Patterns](#configuration-patterns)
- [What NOT to Copy](#what-not-to-copy)

---

## Why Hummingbot?

**Similarities to AnyhowMoomoo:**
- ✅ Python-based trading system
- ✅ Exchange API wrapper architecture
- ✅ Strategy framework with pluggable strategies
- ✅ Order lifecycle management
- ✅ Risk controls and position sizing
- ✅ Real-time market data handling

**Differences (Keep in mind):**
- ❌ They focus on HFT/market-making (we're swing trading)
- ❌ They support 50+ exchanges (we only need moomoo)
- ❌ Heavy Cython optimization (we don't need this)
- ❌ Complex cross-exchange arbitrage (not our use case)

**Key Takeaway:** Borrow architectural patterns and proven interfaces, but keep our implementation simpler.

---

## Phase 2: Connector Architecture

### Connector Base Class Pattern

**File Reference:** `hummingbot/connector/connector_base.py`

**Core Concept:** Abstract base class that standardizes exchange interactions.

```python
# Adapted from Hummingbot's ConnectorBase pattern
# Reference: hummingbot/connector/connector_base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from data.models import Order, Position, OrderRequest, OrderSide

class ExchangeConnectorBase(ABC):
    """
    Base class for exchange connectors.
    Standardizes interaction with different exchanges.
    """
    
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self._ready = False
        
    # ========================================
    # Abstract Methods (Must Implement)
    # ========================================
    
    @abstractmethod
    async def get_balance(self, asset: str) -> Decimal:
        """Get available balance for an asset."""
        pass
    
    @abstractmethod
    async def get_all_balances(self) -> Dict[str, Decimal]:
        """Get all balances for the account."""
        pass
    
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> str:
        """
        Place an order on the exchange.
        Returns order_id.
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get current status of an order."""
        pass
    
    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        pass
    
    # ========================================
    # Common Helper Methods
    # ========================================
    
    def ready(self) -> bool:
        """Is the connector ready for trading?"""
        return self._ready
    
    async def check_connection(self) -> bool:
        """Verify connection to exchange."""
        try:
            await self.get_all_balances()
            self._ready = True
            return True
        except Exception:
            self._ready = False
            return False


# ========================================
# Moomoo Implementation Example
# ========================================

class MoomooConnector(ExchangeConnectorBase):
    """
    Connector for moomoo using OpenD.
    Wraps our existing OpenDConnection class.
    """
    
    def __init__(self, opend_connection):
        super().__init__("moomoo")
        self.opend = opend_connection
        self._order_cache = {}
    
    async def get_balance(self, asset: str) -> Decimal:
        """Get balance from moomoo account."""
        # TODO: Implement using moomoo API
        # ret, data = self.opend.trade_ctx.get_account_info()
        pass
    
    async def place_order(self, order: OrderRequest) -> str:
        """
        Place order via moomoo.
        
        Maps our OrderRequest to moomoo's format.
        """
        # TODO: Implement moomoo order placement
        # Convert OrderRequest to moomoo format
        # ret, data = self.opend.trade_ctx.place_order(...)
        # Store in cache for tracking
        pass
```

**Key Learnings:**
1. **Abstract base class** defines the contract all exchange connectors must fulfill
2. **Async methods** for all I/O operations (network calls)
3. **Standardized return types** using our Pydantic models
4. **Ready state** to prevent trading before connection is established
5. **Order cache** for tracking orders between API calls

---

## Phase 2: Data Models & Types

### Order Book Data Structure

**File Reference:** `hummingbot/core/data_type/order_book.pyx`

**Note:** They use Cython for performance, but we can use pure Python.

```python
# Simplified order book structure
# Reference: hummingbot/core/data_type/order_book.pyx

from decimal import Decimal
from typing import Dict, List, Tuple
from datetime import datetime

class OrderBookRow:
    """Single order book entry (price, quantity)."""
    
    def __init__(self, price: Decimal, quantity: Decimal, update_id: int):
        self.price = price
        self.quantity = quantity
        self.update_id = update_id

class OrderBook:
    """
    Maintains current order book state.
    Useful for strategies that need depth information.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: Dict[Decimal, OrderBookRow] = {}  # price -> row
        self.asks: Dict[Decimal, OrderBookRow] = {}  # price -> row
        self.last_update_id = 0
        self.last_update_time = datetime.now()
    
    def apply_snapshot(self, bids: List[Tuple[Decimal, Decimal]], 
                       asks: List[Tuple[Decimal, Decimal]]):
        """Replace entire order book with snapshot."""
        self.bids.clear()
        self.asks.clear()
        
        for price, qty in bids:
            self.bids[price] = OrderBookRow(price, qty, self.last_update_id)
        
        for price, qty in asks:
            self.asks[price] = OrderBookRow(price, qty, self.last_update_id)
    
    def apply_diff(self, bids: List[Tuple[Decimal, Decimal]], 
                   asks: List[Tuple[Decimal, Decimal]]):
        """Apply incremental update to order book."""
        for price, qty in bids:
            if qty == 0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = OrderBookRow(price, qty, self.last_update_id)
        
        for price, qty in asks:
            if qty == 0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = OrderBookRow(price, qty, self.last_update_id)
    
    def get_best_bid(self) -> Decimal:
        """Get highest bid price."""
        return max(self.bids.keys()) if self.bids else Decimal("0")
    
    def get_best_ask(self) -> Decimal:
        """Get lowest ask price."""
        return min(self.asks.keys()) if self.asks else Decimal("0")
    
    def get_mid_price(self) -> Decimal:
        """Get mid-market price."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        return (bid + ask) / 2 if bid and ask else Decimal("0")
```

**Key Learnings:**
1. **Snapshot vs diff updates** - handle both full and incremental updates
2. **Update IDs** for tracking order book version
3. **Helper methods** for common queries (best bid/ask, mid price)
4. **Dict-based storage** for fast price lookups

---

## Phase 3: Strategy Framework

### Strategy Base Class

**File Reference:** `hummingbot/strategy/strategy_base.py`

```python
# Adapted Strategy Base Pattern
# Reference: hummingbot/strategy/strategy_base.py

from abc import ABC, abstractmethod
from typing import List, Dict
from data.models import TradePlan, MarketSnapshot, Position

class StrategyBase(ABC):
    """
    Base class for all trading strategies.
    
    Event-driven: Reacts to market data and order updates.
    """
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.active = False
        self._positions: Dict[str, Position] = {}
    
    # ========================================
    # Lifecycle Methods
    # ========================================
    
    def start(self):
        """Called when strategy is activated."""
        self.active = True
        self.on_start()
    
    def stop(self):
        """Called when strategy is deactivated."""
        self.active = False
        self.on_stop()
    
    @abstractmethod
    def on_start(self):
        """Override to add custom startup logic."""
        pass
    
    @abstractmethod
    def on_stop(self):
        """Override to add custom cleanup logic."""
        pass
    
    # ========================================
    # Market Data Events
    # ========================================
    
    @abstractmethod
    def on_tick(self, snapshot: MarketSnapshot):
        """
        Called on every market data update.
        
        Main strategy logic goes here.
        """
        pass
    
    # ========================================
    # Order Events
    # ========================================
    
    def on_order_filled(self, order_id: str, fill_price: Decimal, fill_qty: Decimal):
        """Called when an order is filled."""
        # Update positions, notify strategy
        self.did_fill_order(order_id, fill_price, fill_qty)
    
    @abstractmethod
    def did_fill_order(self, order_id: str, fill_price: Decimal, fill_qty: Decimal):
        """Override to react to order fills."""
        pass
    
    # ========================================
    # Trade Plan Generation
    # ========================================
    
    @abstractmethod
    def generate_trade_plans(self, snapshot: MarketSnapshot) -> List[TradePlan]:
        """
        Generate trade plans based on current market state.
        
        Returns list of proposed trades.
        """
        pass
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def has_position(self, symbol: str) -> bool:
        """Check if we have an open position in this symbol."""
        return symbol in self._positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol."""
        return self._positions.get(symbol)


# ========================================
# Example: Simple Momentum Strategy
# ========================================

class MomentumStrategy(StrategyBase):
    """
    Example swing strategy using momentum signals.
    """
    
    def __init__(self, config: dict):
        super().__init__("momentum_swing", config)
        self.lookback_period = config.get("lookback_period", 20)
        self.entry_threshold = config.get("entry_threshold", 0.02)  # 2%
    
    def on_start(self):
        """Initialize strategy-specific state."""
        print(f"Starting {self.name} strategy")
    
    def on_stop(self):
        """Cleanup."""
        print(f"Stopping {self.name} strategy")
    
    def on_tick(self, snapshot: MarketSnapshot):
        """
        Main strategy logic.
        
        Called every time we get new market data.
        """
        if not self.active:
            return
        
        # Check if we should generate new trade plans
        plans = self.generate_trade_plans(snapshot)
        
        # Plans would be sent to validator/execution engine
        return plans
    
    def generate_trade_plans(self, snapshot: MarketSnapshot) -> List[TradePlan]:
        """
        Generate trade plan if momentum conditions are met.
        """
        plans = []
        
        # Skip if we already have a position
        if self.has_position(snapshot.symbol):
            return plans
        
        # Calculate momentum
        if len(snapshot.daily_bars) < self.lookback_period:
            return plans
        
        # Example: Simple price momentum
        current_price = snapshot.current_price
        lookback_price = snapshot.daily_bars[-self.lookback_period].close
        momentum = (current_price - lookback_price) / lookback_price
        
        # Generate long signal if momentum is strong
        if momentum > self.entry_threshold:
            plan = TradePlan(
                plan_id=f"momentum_{snapshot.symbol}_{datetime.now().timestamp()}",
                symbol=snapshot.symbol,
                direction=OrderSide.BUY,
                rationale=f"Momentum signal: {momentum:.2%} over {self.lookback_period} days",
                timeframe="swing",
                expected_hold_days=5,
                entry_price=current_price,
                stop_price=current_price * Decimal("0.95"),  # 5% stop
                target_prices=[current_price * Decimal("1.10")],  # 10% target
                allocation_risk_pct=Decimal("1.5"),
                created_at=datetime.now(),
            )
            plans.append(plan)
        
        return plans
    
    def did_fill_order(self, order_id: str, fill_price: Decimal, fill_qty: Decimal):
        """React to order fills."""
        print(f"Order {order_id} filled at {fill_price}, qty: {fill_qty}")
```

**Key Learnings:**
1. **Event-driven design** - strategies react to events, don't poll
2. **Lifecycle hooks** (start/stop) for setup/cleanup
3. **Separate signal generation from execution** - strategies propose, execution layer decides
4. **Position tracking** built into base class
5. **Config-driven parameters** for easy tuning

---

## Phase 4: Order Tracking & Lifecycle

### Order Tracker Pattern

**File Reference:** `hummingbot/connector/exchange/*/exchange_order_tracker.py`

```python
# Order Tracking Pattern
# Reference: hummingbot/connector/exchange/binance/binance_order_tracker.py

from typing import Dict, Optional
from datetime import datetime
from data.models import Order, OrderStatus
from enum import Enum

class OrderState(Enum):
    """Order lifecycle states."""
    PENDING = "PENDING"          # Created locally, not yet submitted
    SUBMITTED = "SUBMITTED"      # Sent to exchange
    OPEN = "OPEN"                # Acknowledged by exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"            # Completely filled
    CANCELLED = "CANCELLED"      # User cancelled
    REJECTED = "REJECTED"        # Exchange rejected
    EXPIRED = "EXPIRED"          # Time-based expiry

class TrackedOrder:
    """Enhanced order with tracking metadata."""
    
    def __init__(self, order: Order):
        self.order = order
        self.state = OrderState.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.fill_events = []  # Track partial fills
        self.last_update_timestamp = 0
    
    def update_state(self, new_state: OrderState):
        """Update order state."""
        self.state = new_state
        self.updated_at = datetime.now()
    
    def add_fill(self, fill_price: Decimal, fill_qty: Decimal, timestamp: int):
        """Record a fill event."""
        self.fill_events.append({
            "price": fill_price,
            "quantity": fill_qty,
            "timestamp": timestamp
        })
        self.order.filled_quantity += fill_qty
        
        # Update average fill price
        total_value = sum(e["price"] * e["quantity"] for e in self.fill_events)
        total_qty = sum(e["quantity"] for e in self.fill_events)
        self.order.avg_fill_price = total_value / total_qty if total_qty else None

class OrderTracker:
    """
    Tracks order lifecycle from creation to completion.
    
    Critical for:
    - Preventing duplicate orders
    - Handling partial fills
    - Reconciling local state with exchange
    """
    
    def __init__(self):
        self._in_flight_orders: Dict[str, TrackedOrder] = {}  # order_id -> TrackedOrder
        self._completed_orders: Dict[str, TrackedOrder] = {}
    
    def start_tracking(self, order: Order) -> TrackedOrder:
        """Begin tracking a new order."""
        tracked = TrackedOrder(order)
        self._in_flight_orders[order.order_id] = tracked
        return tracked
    
    def process_order_update(self, order_id: str, update: dict):
        """
        Process an order update from the exchange.
        
        Called when we receive WebSocket updates or REST responses.
        """
        if order_id not in self._in_flight_orders:
            # Unknown order, might be from another session
            return
        
        tracked = self._in_flight_orders[order_id]
        
        # Parse status from exchange format
        status = self._parse_order_status(update)
        
        if status == OrderStatus.FILLED:
            tracked.update_state(OrderState.FILLED)
            # Move to completed
            self._completed_orders[order_id] = tracked
            del self._in_flight_orders[order_id]
        
        elif status == OrderStatus.PARTIALLY_FILLED:
            tracked.update_state(OrderState.PARTIALLY_FILLED)
            # Record fill if new
            fill_qty = update.get("filled_quantity")
            if fill_qty > tracked.order.filled_quantity:
                new_fill_qty = fill_qty - tracked.order.filled_quantity
                tracked.add_fill(
                    update.get("last_fill_price"),
                    new_fill_qty,
                    update.get("timestamp")
                )
        
        elif status == OrderStatus.CANCELLED:
            tracked.update_state(OrderState.CANCELLED)
            self._completed_orders[order_id] = tracked
            del self._in_flight_orders[order_id]
    
    def is_order_in_flight(self, order_id: str) -> bool:
        """Check if order is still active."""
        return order_id in self._in_flight_orders
    
    def get_open_orders(self) -> List[TrackedOrder]:
        """Get all orders that are not yet completed."""
        return [
            tracked for tracked in self._in_flight_orders.values()
            if tracked.state in [OrderState.OPEN, OrderState.PARTIALLY_FILLED]
        ]
    
    def _parse_order_status(self, update: dict) -> OrderStatus:
        """Convert exchange-specific status to our OrderStatus enum."""
        # TODO: Implement moomoo-specific parsing
        pass
```

**Key Learnings:**
1. **Separate tracking object** from base Order model
2. **State machine** for order lifecycle
3. **Partial fill handling** with event history
4. **In-flight vs completed** segregation
5. **Average fill price** calculation for partial fills

---

## Phase 4: Risk Management & Position Sizing

### Position Sizing

**File Reference:** Various strategy implementations

```python
# Position Sizing Formulas
# Reference: Extracted from multiple Hummingbot strategies

from decimal import Decimal
from typing import Optional

class PositionSizer:
    """
    Calculate position sizes based on risk parameters.
    
    Critical for small account management.
    """
    
    def __init__(self, config: dict):
        self.min_notional = Decimal(str(config.get("min_notional", 10)))
        self.max_notional = Decimal(str(config.get("max_notional", 50)))
        self.fractional_shares = config.get("fractional_shares", True)
    
    def calculate_position_size(
        self,
        account_balance: Decimal,
        risk_per_trade_pct: Decimal,
        entry_price: Decimal,
        stop_price: Decimal,
    ) -> Decimal:
        """
        Calculate position size based on risk %.
        
        Formula: Position Size = (Account Balance * Risk%) / (Entry - Stop)
        
        Args:
            account_balance: Current account equity
            risk_per_trade_pct: % of account to risk (e.g., 1.5 for 1.5%)
            entry_price: Planned entry price
            stop_price: Stop loss price
        
        Returns:
            Position size in dollars
        """
        # Calculate risk amount in dollars
        risk_amount = account_balance * (risk_per_trade_pct / Decimal("100"))
        
        # Calculate distance to stop (risk per share)
        price_risk = abs(entry_price - stop_price)
        
        if price_risk == 0:
            raise ValueError("Entry and stop price cannot be the same")
        
        # Position size = risk amount / risk per share
        shares = risk_amount / price_risk
        position_value = shares * entry_price
        
        # Apply min/max limits
        position_value = self._clamp_to_limits(position_value)
        
        return position_value
    
    def calculate_shares_from_notional(
        self,
        notional: Decimal,
        price: Decimal,
    ) -> Decimal:
        """Convert dollar amount to shares."""
        shares = notional / price
        
        if not self.fractional_shares:
            shares = shares.quantize(Decimal("1"), rounding="ROUND_DOWN")
        
        return shares
    
    def _clamp_to_limits(self, value: Decimal) -> Decimal:
        """Ensure value is within min/max bounds."""
        if value < self.min_notional:
            return Decimal("0")  # Too small, don't trade
        if value > self.max_notional:
            return self.max_notional
        return value


class RiskManager:
    """
    Portfolio-level risk controls.
    
    Prevents over-leveraging and excessive concentration.
    """
    
    def __init__(self, config: dict):
        self.max_open_positions = config.get("max_open_positions", 3)
        self.max_sector_exposure_pct = Decimal(str(config.get("max_sector_exposure_pct", 40)))
        self.max_single_position_pct = Decimal(str(config.get("max_single_position_pct", 20)))
    
    def can_open_position(
        self,
        current_positions: int,
        new_position_size: Decimal,
        account_balance: Decimal,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if we can safely open a new position.
        
        Returns:
            (can_open, reason_if_not)
        """
        # Check position count
        if current_positions >= self.max_open_positions:
            return False, f"Max positions reached: {self.max_open_positions}"
        
        # Check position size relative to account
        position_pct = (new_position_size / account_balance) * Decimal("100")
        if position_pct > self.max_single_position_pct:
            return False, f"Position too large: {position_pct:.1f}% > {self.max_single_position_pct}%"
        
        return True, None
    
    def check_sector_exposure(
        self,
        sector: str,
        new_position_size: Decimal,
        current_sector_exposure: Decimal,
        account_balance: Decimal,
    ) -> tuple[bool, Optional[str]]:
        """Check if adding this position would exceed sector limits."""
        total_sector_exposure = current_sector_exposure + new_position_size
        exposure_pct = (total_sector_exposure / account_balance) * Decimal("100")
        
        if exposure_pct > self.max_sector_exposure_pct:
            return False, f"Sector exposure too high: {exposure_pct:.1f}%"
        
        return True, None
```

**Key Learnings:**
1. **Risk-based sizing** - size positions by how much you're willing to lose
2. **Min/max notional** - critical for small accounts with fractional shares
3. **Portfolio-level limits** - prevent over-concentration
4. **Sector exposure** - diversification across different stocks/sectors
5. **Pre-trade validation** - check all limits before submitting orders

---

## Phase 4: Event System

### Event-Driven Architecture

**File Reference:** `hummingbot/core/event/event_forwarder.py`, `hummingbot/core/event/events.py`

```python
# Event System Pattern
# Reference: hummingbot/core/event/

from enum import Enum
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

class EventType(Enum):
    """Types of events in the system."""
    # Market data events
    MARKET_TICK = "MARKET_TICK"
    ORDER_BOOK_UPDATE = "ORDER_BOOK_UPDATE"
    
    # Order events
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    
    # Position events
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    
    # Risk events
    RISK_LIMIT_BREACH = "RISK_LIMIT_BREACH"

@dataclass
class Event:
    """Base event object."""
    type: EventType
    timestamp: datetime
    data: Dict[str, Any]

class EventBus:
    """
    Central event bus for pub/sub pattern.
    
    Decouples components - they don't need to know about each other.
    """
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._listeners:
            self._listeners[event_type].remove(callback)
    
    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        if event.type in self._listeners:
            for callback in self._listeners[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log error but don't let one handler crash others
                    print(f"Error in event handler: {e}")

# ========================================
# Usage Example
# ========================================

# In your daemon/main.py:
event_bus = EventBus()

# Strategy subscribes to market data
def on_market_tick(event: Event):
    snapshot = event.data["snapshot"]
    # Generate trade plans
    plans = strategy.generate_trade_plans(snapshot)

event_bus.subscribe(EventType.MARKET_TICK, on_market_tick)

# Execution engine subscribes to order fills
def on_order_filled(event: Event):
    order_id = event.data["order_id"]
    fill_price = event.data["fill_price"]
    # Update positions, notify strategy
    
event_bus.subscribe(EventType.ORDER_FILLED, on_order_filled)

# When market data arrives:
event = Event(
    type=EventType.MARKET_TICK,
    timestamp=datetime.now(),
    data={"snapshot": market_snapshot}
)
event_bus.publish(event)
```

**Key Learnings:**
1. **Pub/Sub pattern** - loose coupling between components
2. **Type-safe events** using Enum
3. **Error isolation** - one handler failure doesn't crash others
4. **Centralized event bus** - single source of truth for all events

---

## Configuration Patterns

### Strategy Configuration

**File Reference:** `conf/strategies/`

```yaml
# Example: conf/strategies/momentum_swing.yml
# Reference: Hummingbot's config structure

strategy:
  name: momentum_swing
  enabled: true

parameters:
  # Symbols to trade
  symbols:
    - AAPL
    - MSFT
    - TSLA
  
  # Technical parameters
  lookback_period: 20          # Days for momentum calculation
  entry_threshold: 0.02        # 2% momentum required for entry
  exit_threshold: 0.01         # 1% for exit
  
  # VWAP parameters
  vwap_distance_max: 0.005     # Max 0.5% from VWAP for entry
  
  # Risk management
  max_risk_per_trade_pct: 1.5  # % of account to risk
  stop_loss_pct: 0.05          # 5% stop loss
  take_profit_pct: 0.10        # 10% take profit
  
  # Position management
  max_hold_days: 7             # Force exit after 7 days
  partial_exit_pct: 0.50       # Take 50% profit at first target

# Override execution mode for this strategy
execution:
  mode: SEMI_AUTOMATIC
```

**Python Config Loader:**

```python
# Load strategy-specific config
import yaml

class StrategyConfigLoader:
    """Load and validate strategy configurations."""
    
    @staticmethod
    def load(strategy_name: str) -> dict:
        """Load strategy config from YAML file."""
        config_path = f"./config/strategies/{strategy_name}.yml"
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required = ["strategy", "parameters"]
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        return config
    
    @staticmethod
    def create_strategy(config: dict):
        """Factory method to instantiate strategy from config."""
        from strategy.registry import StrategyRegistry
        
        strategy_name = config["strategy"]["name"]
        parameters = config["parameters"]
        
        # Get strategy class from registry
        strategy_class = StrategyRegistry.get(strategy_name)
        
        # Instantiate with parameters
        return strategy_class(parameters)
```

**Key Learnings:**
1. **YAML for configuration** - human-readable, easy to edit
2. **Strategy-specific configs** - each strategy has its own file
3. **Factory pattern** for instantiation
4. **Validation** - fail fast if config is invalid

---

## What NOT to Copy

### ❌ Avoid These Patterns

1. **Cython Optimization**
   - File: `*.pyx` files
   - Why: Adds complexity, premature optimization
   - Alternative: Pure Python is fast enough for swing trading

2. **Complex Multi-Exchange Arbitrage**
   - File: `hummingbot/strategy/cross_exchange_*`
   - Why: Not relevant for single-exchange swing trading
   - Alternative: Focus on simple directional strategies

3. **Market Making Inventory Management**
   - File: `hummingbot/strategy/pure_market_making/`
   - Why: Market making is different from swing trading
   - Alternative: Simple position tracking is sufficient

4. **HFT Latency Optimizations**
   - Various files with microsecond timing
   - Why: Swing trading doesn't need microsecond precision
   - Alternative: Second-level granularity is fine

5. **Complex Order Types**
   - Multiple exotic order types (iceberg, TWAP, etc.)
   - Why: Start with simple market/limit orders
   - Alternative: Add complexity only if needed

---

## Implementation Roadmap

### Phase 2: Data & Connectors (Use These Patterns)
- ✅ `ExchangeConnectorBase` - abstract connector interface
- ✅ `OrderBook` - order book management
- ✅ Async patterns for network I/O

### Phase 3: Strategy Framework (Use These Patterns)
- ✅ `StrategyBase` - event-driven strategy pattern
- ✅ `EventBus` - pub/sub for decoupling
- ✅ YAML-based strategy configuration

### Phase 4: Execution & Risk (Use These Patterns)
- ✅ `OrderTracker` - order lifecycle management
- ✅ `PositionSizer` - risk-based position sizing
- ✅ `RiskManager` - portfolio-level limits
- ✅ Event system for order updates

---

## Next Steps

When you're ready to build each phase:

1. **Review this document** for the relevant section
2. **Study the pattern** - understand why it's designed that way
3. **Adapt to our needs** - simplify for our use case (swing, single exchange)
4. **Implement incrementally** - one pattern at a time
5. **Test thoroughly** - each component should work standalone

**Remember:** We're borrowing proven patterns, not copying their complexity. Keep it simple!

---

## Additional Resources

- [Hummingbot Documentation](https://hummingbot.org/)
- [Hummingbot GitHub](https://github.com/hummingbot/hummingbot)
- [Hummingbot Discord](https://discord.gg/hummingbot) - Active community for questions

**This is a living document.** Add notes as we learn more during implementation.
