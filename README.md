# Binance Futures Trading Bot

A command-line trading bot for Binance Futures with support for market and limit orders.

## Prerequisites

- Python 3.8 or higher
- Binance API credentials (API Key and Secret)

## Setup Instructions

### 1. Install Dependencies

If you haven't already set up a virtual environment:

```bash
# Create virtual environment (if not already created)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install required packages
pip install -r requirements.txt
```

### 2. Configure API Credentials

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Binance API credentials:
   ```env
   BINANCE_API_KEY=your_actual_api_key_here
   BINANCE_API_SECRET=your_actual_api_secret_here
   FUTURES_TESTNET=true  # Set to false for live trading
   ```

3. **Get your API keys:**
   - **For Testnet (Recommended for testing):** https://testnet.binancefuture.com/
   - **For Live Trading:** https://www.binance.com/en/my/settings/api-management

   ⚠️ **Important:** Start with testnet (`FUTURES_TESTNET=true`) to test the bot safely!

## Running the Bot

### Method 1: Using the entry point script

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the bot
python run_bot.py
```

### Method 2: Direct execution (if executable)

```bash
./run_bot.py
```

### Method 3: Using Python module

```bash
python -m src.cli
```

## Usage Examples

### Place a Market Order

```bash
python run_bot.py market BTCUSDT buy 0.001
```

This places a market buy order for 0.001 BTC.

### Place a Limit Order

```bash
python run_bot.py limit BTCUSDT sell 0.001 50000
```

This places a limit sell order for 0.001 BTC at $50,000.

### Command Syntax

**Market Order:**
```bash
python run_bot.py market <SYMBOL> <SIDE> <QUANTITY>
```

**Limit Order:**
```bash
python run_bot.py limit <SYMBOL> <SIDE> <QUANTITY> <PRICE>
```

**Parameters:**
- `SYMBOL`: Trading pair (e.g., BTCUSDT, ETHUSDT)
- `SIDE`: `buy` or `sell`
- `QUANTITY`: Amount to trade
- `PRICE`: Limit price (only for limit orders)

## Help

To see all available commands:

```bash
python run_bot.py --help
```

## Safety Features

- ✅ Testnet mode enabled by default
- ✅ Input validation for all parameters
- ✅ Comprehensive error handling
- ✅ Detailed logging
- ✅ Symbol validation before trading

## Troubleshooting

### "Module not found" errors
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt`

### "API key not found" errors
- Check that `.env` file exists in the project root
- Verify your API keys are correctly set in `.env`
- Ensure no extra spaces around the `=` sign in `.env`

### Connection errors
- Check your internet connection
- Verify you're using the correct testnet/live endpoint
- Ensure your API keys have futures trading permissions

## Project Structure

```
binance_futures_bot/
├── run_bot.py          # Main entry point
├── .env.example        # Environment variables template
├── .env                # Your actual credentials (not in git)
├── requirements.txt    # Python dependencies
└── src/
    ├── cli.py          # Command-line interface
    ├── client.py       # Binance API client wrapper
    ├── config.py       # Configuration management
    ├── logger.py       # Logging setup
    ├── market_orders.py # Market order implementation
    ├── limit_orders.py # Limit order implementation
    └── validators.py   # Input validation
```

## License

This project is for educational purposes. Use at your own risk.
