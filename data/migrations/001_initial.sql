-- Initial database schema for AnyhowMoomoo market data storage
-- Version: 001
-- Created: 2026-02-23

-- ============================================================================
-- BARS TABLE: Historical OHLCV data
-- ============================================================================
CREATE TABLE IF NOT EXISTS bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,  -- Unix timestamp (seconds since epoch)
    timeframe TEXT NOT NULL,     -- '1d', '1h', '5m', '1m', etc.
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timestamp, timeframe)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_bars_symbol_time 
    ON bars(symbol, timestamp DESC);
    
CREATE INDEX IF NOT EXISTS idx_bars_timeframe 
    ON bars(timeframe, timestamp DESC);
    
CREATE INDEX IF NOT EXISTS idx_bars_created 
    ON bars(created_at DESC);

-- ============================================================================
-- QUOTES TABLE: Real-time bid/ask/last prices
-- ============================================================================
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    bid REAL,
    ask REAL,
    last REAL,
    bid_size INTEGER,
    ask_size INTEGER,
    volume INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_quotes_symbol_time 
    ON quotes(symbol, timestamp DESC);

-- ============================================================================
-- INDICATORS TABLE: Pre-calculated technical indicators
-- ============================================================================
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    indicator_name TEXT NOT NULL,  -- 'vwap', 'rsi', 'atr', etc.
    value REAL NOT NULL,
    metadata TEXT,  -- JSON for additional data (e.g., VWAP bands, RSI levels)
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    UNIQUE(symbol, timestamp, timeframe, indicator_name)
);

CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time 
    ON indicators(symbol, timestamp DESC, indicator_name);

-- ============================================================================
-- TRADE_HISTORY TABLE: Historical trades for Kelly parameter estimation
-- ============================================================================
CREATE TABLE IF NOT EXISTS trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_time INTEGER NOT NULL,
    exit_time INTEGER,
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('long', 'short')),
    pnl REAL,
    pnl_percent REAL,
    status TEXT NOT NULL CHECK(status IN ('open', 'closed', 'cancelled')),
    strategy TEXT,  -- Which strategy generated this trade
    notes TEXT,     -- Additional context
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol 
    ON trade_history(symbol, entry_time DESC);
    
CREATE INDEX IF NOT EXISTS idx_trades_status 
    ON trade_history(status, entry_time DESC);
    
CREATE INDEX IF NOT EXISTS idx_trades_strategy 
    ON trade_history(strategy, entry_time DESC);

-- ============================================================================
-- SCHEMA_MIGRATIONS TABLE: Track applied migrations
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Record this migration
INSERT OR IGNORE INTO schema_migrations (version, name) 
VALUES (1, '001_initial');
