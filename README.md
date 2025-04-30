# Bubblemaps Telegram Bot

A powerful Telegram bot that provides detailed token analysis using Bubblemaps, including bubble maps, token metrics, and decentralization scores.

## Features

- Multi-chain support (ETH, BSC, FTM, AVAX, CRO, ARBI, POLY, BASE, SOL, SONIC)
- Token analysis with bubble map visualization
- Key metrics (price, market cap, volume)
- Decentralization scoring
- Holder analysis
- Clean Telegram UI/UX

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```
4. Create a `.env` file with your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
5. Run the bot:
   ```bash
   python main.py
   ```

## Commands

- `/start` - Welcome message and usage instructions
- `/help` - Show command usage examples
- `/analyze <address> on <chain>` - Analyze a token (e.g., `/analyze 0xABC123 on ETH`)

## Project Structure

- `main.py` - Main bot file
- `config.py` - Configuration settings
- `utils/` - Helper functions
  - `bubblemaps.py` - Bubblemaps API integration
  - `screenshot.py` - Screenshot generation
  - `token_metrics.py` - Token metrics collection 