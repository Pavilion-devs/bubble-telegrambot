from typing import Dict, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ====================================================================
# Development/Production Settings
# ====================================================================
# Set to True to use mock APIs, False to use real APIs
# IMPORTANT: Set this to False for production!
DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'

# Mock API base URL (only used when DEV_MODE is True)
MOCK_API_BASE = "http://127.0.0.1:8000"
# ====================================================================

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Supported Chains
SUPPORTED_CHAINS: Dict[str, str] = {
    "ETH": "Ethereum",
    "BSC": "Binance Smart Chain",
    "FTM": "Fantom",
    "AVAX": "Avalanche",
    "CRO": "Cronos",
    "ARBI": "Arbitrum",
    "POLY": "Polygon",
    "BASE": "Base",
    "SOL": "Solana",
    "SONIC": "Sonic"
}

# API Endpoints
BUBBLEMAPS_API_BASE = "https://api-legacy.bubblemaps.io"
BUBBLEMAPS_API_KEY = os.getenv('BUBBLEMAPS_API_KEY', None)  # Optional API key for computing new maps
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
DEXSCREENER_API_BASE = "https://api.dexscreener.com/latest"

# Mock API Endpoints
MOCK_BUBBLEMAPS_API_BASE = f"{MOCK_API_BASE}"
MOCK_COINGECKO_API_BASE = f"{MOCK_API_BASE}/coingecko/api/v3"
MOCK_DEXSCREENER_API_BASE = f"{MOCK_API_BASE}/dexscreener/latest"

# Screenshot Settings
SCREENSHOT_WIDTH = 1200
SCREENSHOT_HEIGHT = 800
SCREENSHOT_TIMEOUT = 60000  # 60 seconds

# Message Templates
WELCOME_MESSAGE = """
👋 Welcome to the Bubblemaps Token Analysis Bot!

I can help you analyze any token across multiple chains. To get started:

1. Click the "🔍 Analyze Token" button below
2. Enter your token address when prompted
3. Select the blockchain network from the list

I'll provide you with:
   - 📊 Token metrics (price, market cap, volume)
   - 🎯 Decentralization score
   - 🧠 Holder analysis
   - 🖼️ Bubble map visualization

Supported chains: {chains}

You can also use the traditional command:
/analyze <address> on <chain>

Need help? Click the "❓ Help" button or use /help for examples!
"""

HELP_MESSAGE = """
📚 Here are some examples of how to use me:

1. Analyze a token on Ethereum:
   /analyze 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 on ETH (UNI)

2. Analyze a token on BSC:
   /analyze 0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82 on BSC (CAKE)

3. Analyze a token on Solana:
   /analyze EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v on SOL (USDC)

You can also use these commands:
- /start - Show welcome message
- /help - Show this help message
""" 