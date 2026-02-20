# Quick Start - 5 Minutes to First Run

This is the express setup guide. For detailed troubleshooting, see [SETUP.md](SETUP.md).

## Prerequisites

- Python 3.10+ installed
- Git installed
- 5 minutes of time

## Step-by-Step (Copy & Paste)

### 1. Clone and Enter Directory

```bash
git clone https://github.com/mandlcho/AnyhowMoomoo.git
cd AnyhowMoomoo/algomoomoo
```

### 2. Install Dependencies

```bash
# Recommended: Create virtual environment first
python -m venv venv

# Activate it (choose your platform):
.\venv\Scripts\activate     # Windows PowerShell
# OR
source venv/bin/activate    # Mac/Linux

# Install packages
pip install -r requirements.txt
```

### 3. Verify Setup

```bash
python scripts/verify_setup.py
```

Expected output:
```
✅ PASS - Python version
✅ PASS - Package imports
✅ PASS - Project structure
✅ PASS - config.yaml
⚠️  FAIL - .env file (not yet created)
```

### 4. Configure Credentials

```bash
# Copy template
cp .env.example .env

# Edit with your editor
notepad .env       # Windows
nano .env          # Linux
vim .env           # If you're fancy
```

Add your moomoo credentials:
```
MOOMOO_USER_ID=12345678
MOOMOO_PASSWORD=your_password
MOOMOO_SECURITY_FIRM=FUTU
```

### 5. Test Configuration (No OpenD Required)

```bash
python scripts/test_config.py
```

Expected output:
```
✅ Config loaded successfully
✅ All required secrets present
```

### 6. Run Unit Tests (No OpenD Required)

```bash
pytest tests/unit/ -v
```

Expected output:
```
tests/unit/test_config.py::test_config_loads PASSED
tests/unit/test_models.py::test_ohlcv_creation PASSED
... (more tests)
```

## You're Done! 🎉

At this point, everything works except the OpenD connection.

### To Run Without OpenD

The configuration, models, and tests all work:

```bash
# Test configuration loading
python scripts/test_config.py

# Run unit tests
pytest tests/unit/ -v

# Explore the code
cat data/models.py
cat daemon/config.py
```

### To Run With OpenD (Optional)

If you have OpenD installed and running:

```bash
# Test OpenD connection
python scripts/test_opend.py

# Run the daemon
python -m daemon.main
```

## What Can You Do Now?

### Immediate (No OpenD)
- ✅ Run `python scripts/test_config.py` - test config loading
- ✅ Run `pytest tests/unit/ -v` - run all unit tests
- ✅ Edit `config/config.yaml` - customize risk settings
- ✅ Explore the codebase - everything is documented

### With OpenD Installed
- ✅ Run `python scripts/test_opend.py` - test connection
- ✅ Run `python -m daemon.main` - start the daemon
- ✅ See live logs in `logs/daemon.log`

## Common Issues

### "Import error: No module named 'pydantic'"
```bash
# Make sure venv is activated (you should see (venv) in prompt)
# Then:
pip install -r requirements.txt
```

### "Config file not found"
```bash
# Make sure you're in the algomoomoo directory
pwd     # Should end with /algomoomoo
ls      # Should show daemon/, data/, config/, etc.
```

### "Missing required secrets"
```bash
# Make sure .env file exists and has real values
cat .env
# Should show MOOMOO_USER_ID and MOOMOO_PASSWORD (not placeholders)
```

## Next Steps

1. **Customize your config** - Edit `config/config.yaml`:
   - Set your risk tolerance (`max_risk_per_trade_pct`)
   - Adjust position sizing for your account size
   - Choose execution mode (SEMI_AUTOMATIC vs AUTOMATIC)

2. **Read the architecture** - See `README.md` for:
   - Project structure
   - Phase 1 status
   - Development roadmap

3. **Ready for Phase 2?** When you want to add:
   - Historical data fetching
   - Technical indicators (RSI, ATR, SMA)
   - VWAP calculations

Just let me know and we'll build it together, one feature at a time!

## Help

- **Detailed setup**: See [SETUP.md](SETUP.md)
- **Project overview**: See [README.md](README.md)
- **Configuration reference**: See [config/config.yaml](config/config.yaml)
