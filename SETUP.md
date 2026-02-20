# Setup Guide - AnyhowMoomoo Trading Daemon

This guide will help you verify your setup step-by-step.

## Prerequisites Checklist

- [ ] Python 3.10 or higher installed
- [ ] Git installed
- [ ] moomoo OpenD downloaded (optional for Phase 1 testing)
- [ ] moomoo account (paper trading account is fine)

## Step 1: Clone and Navigate

```bash
git clone https://github.com/mandlcho/AnyhowMoomoo.git
cd AnyhowMoomoo/algomoomoo
```

## Step 2: Verify Python Version

```bash
python --version
# Should show Python 3.10.x or higher
```

If you need to use a specific Python version:
```bash
python3.10 --version
# or
python3.11 --version
```

## Step 3: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (CMD):
.\venv\Scripts\activate.bat

# On Linux/Mac:
source venv/bin/activate
```

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed futu-api-x.x.x pydantic-x.x.x pyyaml-x.x.x ...
```

## Step 5: Verify Installation

Run the verification script:
```bash
python scripts/verify_setup.py
```

This will check:
- All required packages are installed
- Package versions are compatible
- Python modules can be imported
- Config files are present

## Step 6: Configure Credentials

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
# On Windows:
notepad .env

# On Linux/Mac:
nano .env
# or
vim .env
```

Fill in your moomoo credentials:
```bash
MOOMOO_USER_ID=your_actual_user_id
MOOMOO_PASSWORD=your_actual_password
MOOMOO_SECURITY_FIRM=FUTU
```

**Important:** Never commit the `.env` file! It's already in `.gitignore`.

## Step 7: Test Configuration Loading

```bash
python scripts/test_config.py
```

This will:
- Load your config.yaml
- Validate all settings
- Show you the current configuration
- NOT connect to OpenD (safe to run without OpenD)

## Step 8: Run Unit Tests (No OpenD Required)

```bash
pytest tests/unit/ -v
```

Expected output:
```
tests/unit/test_config.py::test_config_loads PASSED
tests/unit/test_models.py::test_ohlcv_creation PASSED
tests/unit/test_models.py::test_order_request_validation PASSED
tests/unit/test_models.py::test_trade_plan_creation PASSED
```

## Step 9: Install and Start OpenD (Optional for Phase 1)

### Download OpenD
1. Go to https://www.moomoo.com/us/support/topic4_68
2. Download OpenD for your platform
3. Install following moomoo's instructions
4. Start OpenD (it should run on localhost:11111 by default)

### Verify OpenD is Running

```bash
# Check if port 11111 is listening
# On Windows:
netstat -an | findstr 11111

# On Linux/Mac:
lsof -i :11111
# or
netstat -an | grep 11111
```

You should see something like:
```
TCP    127.0.0.1:11111    LISTENING
```

## Step 10: Test OpenD Connection

**Only run this if OpenD is running!**

```bash
python scripts/test_opend.py
```

This will:
- Connect to OpenD quote context
- Test trade context unlock
- Show connection status
- Disconnect cleanly

## Step 11: Run the Daemon

```bash
python -m daemon.main
```

Expected output:
```
============================================================
Trading Daemon Starting - Phase 1
============================================================
Execution mode: SEMI_AUTOMATIC
Paper trading: True
Max risk per trade: 1.5%
Testing OpenD connection...
✓ Quote context connected
✓ Trade context connected and unlocked
Health check: {'quote_connected': True, 'trade_connected': True}
Daemon ready. Press Ctrl+C to stop.
```

Press `Ctrl+C` to stop the daemon.

## Troubleshooting

### Python Version Issues
**Problem:** `python --version` shows Python 2.x or < 3.10

**Solution:**
```bash
# Try python3
python3 --version

# Or specify version explicitly
python3.10 -m venv venv
```

### Import Errors
**Problem:** `ModuleNotFoundError: No module named 'pydantic'`

**Solution:**
```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# Reinstall dependencies
pip install -r requirements.txt
```

### Config File Not Found
**Problem:** `FileNotFoundError: Config file not found`

**Solution:**
```bash
# Make sure you're in the algomoomoo directory
pwd  # or cd on Windows
ls config/config.yaml  # Should exist
```

### OpenD Connection Fails
**Problem:** `ConnectionError: Failed to unlock trade`

**Solutions:**
1. Check OpenD is running:
   ```bash
   netstat -an | findstr 11111  # Windows
   lsof -i :11111               # Mac/Linux
   ```

2. Verify credentials in `.env` are correct

3. Check OpenD logs for errors

4. Try paper trading first (`paper_trading: true` in config.yaml)

### YAML Parse Errors
**Problem:** `yaml.scanner.ScannerError`

**Solution:**
- Check `config/config.yaml` for proper indentation (use spaces, not tabs)
- Validate YAML syntax: https://www.yamllint.com/

## What's Working vs Not Working (Phase 1)

### ✅ Working Now
- Configuration loading (YAML + env vars)
- Data model validation (Pydantic)
- OpenD connection and authentication
- Logging setup
- Unit tests
- Project structure

### ⏳ Not Yet Implemented (Future Phases)
- Historical data fetching → Phase 2
- Technical indicators → Phase 2  
- VWAP calculations → Phase 2
- Claude integration → Phase 3
- Trade plan validation → Phase 3
- Order execution → Phase 4
- Position management → Phase 4
- TUI/Web UI → Phase 5

## Next Steps

Once everything above works:

1. **Explore the codebase:**
   ```bash
   # See project structure
   tree  # or ls -R
   
   # Read the models
   cat data/models.py
   
   # Check the config
   cat config/config.yaml
   ```

2. **Customize configuration:**
   - Edit `config/config.yaml` to match your risk tolerance
   - Adjust position sizing for your account size

3. **Run tests regularly:**
   ```bash
   pytest tests/unit/ -v
   ```

4. **Ready for Phase 2?** Let me know and we'll build:
   - Historical data fetching for a single symbol
   - Basic technical indicators (SMA, RSI, ATR)
   - Data storage and caching

## Getting Help

If something doesn't work:
1. Check this guide's troubleshooting section
2. Run `python scripts/verify_setup.py` to diagnose
3. Check logs in `logs/daemon.log`
4. Review error messages carefully - they usually tell you what's wrong!

## Success Criteria

You know it's working when:
- ✅ `pytest tests/unit/ -v` passes all tests
- ✅ `python -m daemon.main` starts without errors (with OpenD running)
- ✅ You see "✓ Quote context connected" and "✓ Trade context connected"
- ✅ Logs appear in `logs/daemon.log`
- ✅ No Python import errors
