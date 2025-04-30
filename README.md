# 🤖 Bubblemaps Telegram Bot

A powerful Telegram bot that provides detailed token analysis using Bubblemaps, including bubble maps, token metrics, and decentralization scores. Get instant insights into any token across multiple blockchain networks.

## ✨ Features

- 🌐 **Multi-chain Support**
  - ETH (Ethereum)
  - BSC (Binance Smart Chain)
  - FTM (Fantom)
  - AVAX (Avalanche)
  - CRO (Cronos)
  - ARBI (Arbitrum)
  - POLY (Polygon)
  - BASE (Base)
  - SOL (Solana)
  - SONIC (Sonic)

- 📊 **Token Analysis**
  - Real-time price and market data
  - Market cap and volume tracking
  - 24h price change monitoring
  - Decentralization scoring
  - Holder distribution analysis
  - Interactive bubble map visualization

- 🎯 **User Experience**
  - Interactive button navigation
  - Clear, emoji-rich messages
  - Graceful error handling
  - Network resilience with auto-retry
  - Intuitive conversation flow

## 🚀 Getting Started

### Prerequisites

1. Python 3.8 or higher
2. pip (Python package manager)
3. A Telegram account
4. [Bubblemaps API Key](https://bubblemaps.io/) (optional, for enhanced features)

### Creating Your Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat with BotFather and send `/newbot`
3. Follow the prompts:
   - Set a name for your bot (e.g., "My Token Analyzer")
   - Choose a username (must end in 'bot', e.g., "my_token_analyzer_bot")
4. BotFather will provide a token. Save this token, you'll need it later!

Optional Bot Settings (via BotFather):
```
/setdescription - Set a description for your bot
/setabouttext - Set the about text
/setuserpic - Set bot profile picture
/setcommands - Set the following commands:
start - Start the bot and see welcome message
analyze - Analyze a token (e.g., /analyze 0xABC123 on ETH)
help - Show help message and examples
cancel - Cancel the current operation
```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bubble-telegrambot.git
   cd bubble-telegrambot
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # On macOS/Linux:
   python -m venv venv
   source venv/bin/activate

   # On Windows:
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers (for screenshot functionality):
   ```bash
   playwright install
   ```

### Configuration

1. Create a `.env` file in the project root:
   ```env
   # Required
   TELEGRAM_BOT_TOKEN=your_bot_token_here

   # Optional
   BUBBLEMAPS_API_KEY=your_api_key_here  # For enhanced features
   DEV_MODE=false                         # Set to true for development
   ```

2. Customize settings in `config.py` if needed:
   - Adjust screenshot dimensions
   - Modify API endpoints
   - Configure supported chains
   - Customize message templates

## 🎮 Usage

### Starting the Bot

```bash
python main.py
```

### Basic Commands

- `/start` - Begin interaction with the bot
- `/help` - Show usage instructions and examples
- `/analyze` - Start token analysis (interactive or with parameters)
- `/cancel` - Cancel current operation

### Analysis Methods

1. **Interactive Flow**:
   - Click "🔍 Analyze Token" button
   - Enter token address when prompted
   - Select blockchain network
   - View analysis results

2. **Direct Command**:
   ```
   /analyze <address> on <chain>
   
   Examples:
   /analyze 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 on ETH
   /analyze 0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82 on BSC
   ```

### Analysis Results

The bot provides:
- 💰 Token price and market cap
- 📈 24h volume and price change
- 🎯 Decentralization score
- 📊 Supply distribution
- 👥 Top holder analysis
- 🖼️ Interactive bubble map visualization

## 🏗️ Project Structure

```
bubble-telegrambot/
├── main.py              # Main bot file
├── config.py            # Configuration settings
├── requirements.txt     # Dependencies
├── .env                 # Environment variables
└── utils/
    ├── bubblemaps.py   # Bubblemaps API integration
    ├── screenshot.py    # Screenshot generation
    ├── token_metrics.py # Token metrics collection
    └── image_helper.py  # Image optimization utilities
```

## 🛠️ Error Handling

The bot includes robust error handling:
- Network connectivity issues
- Invalid token addresses
- Unsupported chains
- API failures
- Screenshot generation errors

Each error provides user-friendly messages with clear next steps.

## 🔄 Conversation Flow

```
Start
├── Welcome Message
│   └── [Analyze Token Button]
│       └── Enter Address Prompt
│           └── Chain Selection
│               └── Analysis Result
├── Help Command
│   └── [Analyze Token Button]
└── /analyze command
    ├── With args -> Direct Analysis
    └── Without args -> Interactive Flow
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the excellent Telegram bot framework
- [Bubblemaps](https://bubblemaps.io/) for their token analysis platform
- All contributors and users of this bot

## 📞 Support

If you encounter any issues or have questions:
1. Check the [Issues](https://github.com/yourusername/bubble-telegrambot/issues) page
2. Create a new issue with detailed information
3. Join our [Telegram Support Group](https://t.me/your_support_group) (if available)

---
Made with ❤️ by [Your Name/Team] 