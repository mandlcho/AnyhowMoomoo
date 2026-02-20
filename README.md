# AnyhowMoomoo Trading Daemon

Local trading system integrating moomoo OpenAPI + OpenD for US equity swing trading.

## Project Status: Phase 1 Complete ✓

### What Works Now
- ✓ Configuration management (YAML + environment variables)
- ✓ OpenD connection wrapper (quote + trade contexts)
- ✓ Structured logging with rotation
- ✓ Core data models (Pydantic)
- ✓ Health checks

### What's Next
- Phase 2: Data fetching, indicators, VWAP
- Phase 3: Strategy logic, Claude integration
- Phase 4: Execution engine, risk management
- Phase 5: TUI/Web UI for trade approval

## Quick Start

### Prerequisites
1. **OpenD installed and running** on localhost:11111
2. **Python 3.10+**
3. **moomoo account** (paper trading supported)

### Setup

```bash
# Clone
git clone https://github.com/mandlcho/AnyhowMoomoo.git
cd AnyhowMoomoo/algomoomoo

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your moomoo credentials

# Review config
vim config/config.yaml

# Run
python -m daemon.main
```

### Configuration

See `config/config.yaml` for all settings:
- **Execution mode**: `SEMI_AUTOMATIC` (manual approval) or `AUTOMATIC`
- **Risk limits**: Max risk per trade, position limits
- **Paper trading**: Default is `true` for safety

## Architecture

```
algomoomoo/
├── daemon/          # Core orchestration
├── connectors/      # OpenD API wrappers
├── data/            # Models, storage, fetching
├── features/        # Indicators, VWAP, feature engineering
├── strategy/        # Filters, Claude interface, validation
├── execution/       # Sizing, risk, order routing
└── ui/              # TUI and web interfaces
```

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires OpenD running)
pytest tests/integration/ -m integration
```

## Development Roadmap

Built incrementally, phase by phase:

**Phase 1** - Core scaffolding ✓  
**Phase 2** - Data & Features  
**Phase 3** - Strategy & Claude Integration  
**Phase 4** - Execution & Risk  
**Phase 5** - UI & Tooling  

## License

MIT
