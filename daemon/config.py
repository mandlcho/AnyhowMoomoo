"""
Configuration management.
Loads from YAML files and environment variables.
"""
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field
from decimal import Decimal

from data.models import (
    ExecutionMode, RiskConfig, SizingConfig, DaemonConfig
)


class ConfigLoader:
    """Loads and validates configuration from YAML + env vars."""
    
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    
    def load(self) -> DaemonConfig:
        """Load and validate configuration."""
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)
        
        # Build risk config
        risk_cfg = raw_config.get("risk", {})
        exec_mode = raw_config.get("execution", {}).get("mode", "SEMI_AUTOMATIC")
        
        # Apply automatic overrides if in AUTOMATIC mode
        if exec_mode == "AUTOMATIC":
            overrides = risk_cfg.get("automatic_overrides", {})
            risk_cfg.update(overrides)
        
        risk = RiskConfig(
            max_risk_per_trade_pct=Decimal(str(risk_cfg.get("max_risk_per_trade_pct", 1.5))),
            max_open_positions=risk_cfg.get("max_open_positions", 3),
            max_sector_exposure_pct=Decimal(str(risk_cfg.get("max_sector_exposure_pct", 40.0))),
            min_liquidity_avg_volume=risk_cfg.get("min_liquidity_avg_volume", 500000),
        )
        
        # Build sizing config
        sizing_cfg = raw_config.get("sizing", {})
        sizing = SizingConfig(
            min_notional_per_trade=Decimal(str(sizing_cfg.get("min_notional_per_trade", 10.0))),
            max_notional_per_trade=Decimal(str(sizing_cfg.get("max_notional_per_trade", 50.0))),
            fractional_shares=sizing_cfg.get("fractional_shares", True),
            min_rr_ratio=Decimal(str(sizing_cfg.get("min_rr_ratio", 2.0))),
        )
        
        # Build daemon config
        opend_cfg = raw_config.get("opend", {})
        account_cfg = raw_config.get("account", {})
        data_cfg = raw_config.get("data", {})
        log_cfg = raw_config.get("logging", {})
        
        config = DaemonConfig(
            execution_mode=ExecutionMode(exec_mode),
            risk=risk,
            sizing=sizing,
            opend_host=opend_cfg.get("host", "127.0.0.1"),
            opend_port=opend_cfg.get("port", 11111),
            paper_trading=account_cfg.get("paper_trading", True),
            cache_dir=data_cfg.get("cache_dir", "./data_cache"),
            log_dir=log_cfg.get("dir", "./logs"),
        )
        
        return config
    
    @staticmethod
    def load_secrets() -> dict:
        """Load secrets from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return {
            "moomoo_user_id": os.getenv("MOOMOO_USER_ID"),
            "moomoo_password": os.getenv("MOOMOO_PASSWORD"),
            "moomoo_security_firm": os.getenv("MOOMOO_SECURITY_FIRM", "FUTU"),
        }
    
    @staticmethod
    def validate_secrets(secrets: dict) -> None:
        """Ensure required secrets are present."""
        required = ["moomoo_user_id", "moomoo_password"]
        missing = [k for k in required if not secrets.get(k)]
        if missing:
            raise ValueError(f"Missing required secrets: {missing}")
