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

## 🚀 START HERE - One-Command Setup

**Easiest way to get started:**

```bash
# Clone the repo
git clone https://github.com/mandlcho/AnyhowMoomoo.git
cd AnyhowMoomoo/algomoomoo

# Run automated setup (Linux/Mac)
bash setup.sh

# OR (Windows)
setup.bat
```

The setup script will:
- ✅ Check Python version (3.10+ required)
- ✅ Install all dependencies
- ✅ Create .env template
- ✅ Run verification tests
- ✅ Show you next steps

**Total time: ~2 minutes**

---

### Manual Setup (If You Prefer)

```bash
# 1. Clone
git clone https://github.com/mandlcho/AnyhowMoomoo.git
cd AnyhowMoomoo/algomoomoo

# 2. Install dependencies
pip install -r requirements.txt

# 3. ✅ VERIFY SETUP (Run this first!)
python scripts/verify_setup.py
```

This will check:
- ✅ Python version
- ✅ All packages installed
- ✅ Project structure
- ✅ Config files

**If verification passes, continue:**

```bash
# 4. Configure credentials
cp .env.example .env
# Edit .env with your moomoo credentials

# 5. Test configuration (no OpenD required)
python scripts/test_config.py

# 6. Run unit tests (no OpenD required)
pytest tests/unit/ -v

# 7. (Optional) Test OpenD connection
python scripts/test_opend.py

# 8. Run the daemon (requires OpenD)
python -m daemon.main
```

### Prerequisites
- **Python 3.10+** (required)
- **moomoo account** (required for live/paper trading)
- **OpenD** (optional for Phase 1 testing)

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
