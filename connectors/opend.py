"""
OpenD connection management.
Wraps moomoo OpenAPI SDK for quote and trade contexts.
"""
import logging
from typing import Optional
from futu import OpenQuoteContext, OpenSecTradeContext, TrdEnv, ModifyOrderOp

logger = logging.getLogger(__name__)


class OpenDConnection:
    """
    Manages connection to local OpenD daemon.
    Provides quote and trade context wrappers.
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
        paper_trading: bool = True,
    ):
        self.host = host
        self.port = port
        self.paper_trading = paper_trading
        
        self._quote_ctx: Optional[OpenQuoteContext] = None
        self._trade_ctx: Optional[OpenSecTradeContext] = None
        
        logger.info(
            f"OpenD connection initialized: {host}:{port}, "
            f"paper_trading={paper_trading}"
        )
    
    def connect_quote(self) -> OpenQuoteContext:
        """Establish quote context connection."""
        if self._quote_ctx is None:
            logger.info("Connecting to OpenD quote context...")
            self._quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            logger.info("Quote context connected.")
        return self._quote_ctx
    
    def connect_trade(
        self,
        user_id: str,
        password: str,
        security_firm: str = "FUTU",
    ) -> OpenSecTradeContext:
        """
        Establish trade context connection.
        Requires unlock for live trading.
        """
        if self._trade_ctx is None:
            trd_env = TrdEnv.SIMULATE if self.paper_trading else TrdEnv.REAL
            logger.info(f"Connecting to OpenD trade context (env={trd_env.name})...")
            
            self._trade_ctx = OpenSecTradeContext(
                host=self.host,
                port=self.port,
                security_firm=security_firm,
            )
            
            # Unlock trading (required even for paper)
            ret_code, ret_data = self._trade_ctx.unlock_trade(password)
            if ret_code != 0:
                raise ConnectionError(f"Failed to unlock trade: {ret_data}")
            
            logger.info("Trade context connected and unlocked.")
        
        return self._trade_ctx
    
    def disconnect(self):
        """Close all connections."""
        if self._quote_ctx:
            self._quote_ctx.close()
            self._quote_ctx = None
            logger.info("Quote context disconnected.")
        
        if self._trade_ctx:
            self._trade_ctx.close()
            self._trade_ctx = None
            logger.info("Trade context disconnected.")
    
    def health_check(self) -> dict:
        """
        Basic health check.
        Returns dict with connection status.
        """
        status = {
            "quote_connected": self._quote_ctx is not None,
            "trade_connected": self._trade_ctx is not None,
        }
        
        # TODO: Add actual ping/heartbeat checks
        
        return status
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
