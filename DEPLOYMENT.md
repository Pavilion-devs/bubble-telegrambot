# Deployment Guide for Bubblemaps Telegram Bot

This guide will help you deploy the Bubblemaps Telegram Bot to a production environment.

## Prerequisites

- Python 3.10+ installed
- A server or VPS (Ubuntu/Debian recommended)
- A Telegram Bot token from BotFather

## Local Development Setup

1. **Clone the repository and install dependencies**:
   ```bash
   git clone https://github.com/yourusername/bubble-bot.git
   cd bubble-bot
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

3. **Set up development environment**:
   ```bash
   # Create .env file
   echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
   
   # Edit config.py to enable development mode
   # Set DEV_MODE = True
   ```

4. **Run the mock API server** (for development only):
   ```bash
   python mock_api.py
   ```

5. **Run the bot in development mode**:
   ```bash
   python main.py
   ```

## Production Deployment

### 1. Server Setup (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git

# Install additional dependencies for Playwright
sudo apt install -y libgtk-3-0 libnotify4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb
```

### 2. Bot Installation

```bash
# Clone repository
git clone https://github.com/yourusername/bubble-bot.git
cd bubble-bot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # For production serving if needed

# Install Playwright browsers
playwright install --with-deps
```

### 3. Configure for Production

1. **Create environment file**:
   ```bash
   echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
   ```

2. **Set production mode**:
   - Edit `config.py` and set `DEV_MODE = False`

3. **Test the bot**:
   ```bash
   python main.py
   ```

### 4. Run as a Service (systemd)

1. **Create a systemd service file**:
   ```bash
   sudo nano /etc/systemd/system/bubblebot.service
   ```

2. **Add the following configuration**:
   ```
   [Unit]
   Description=Bubblemaps Telegram Bot
   After=network.target

   [Service]
   User=your_username
   Group=your_username
   WorkingDirectory=/path/to/bubble-bot
   Environment="PATH=/path/to/bubble-bot/venv/bin"
   ExecStart=/path/to/bubble-bot/venv/bin/python main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable bubblebot
   sudo systemctl start bubblebot
   ```

4. **Check status**:
   ```bash
   sudo systemctl status bubblebot
   ```

5. **View logs**:
   ```bash
   sudo journalctl -u bubblebot -f
   ```

## Using Docker (Alternative)

### 1. Create a Dockerfile

Create a file named `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# Install dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Run the bot
CMD ["python", "main.py"]
```

### 2. Create a docker-compose.yml file

```yaml
version: '3'

services:
  bubblebot:
    build: .
    restart: always
    environment:
      - TELEGRAM_BOT_TOKEN=your_token_here
    volumes:
      - ./:/app
```

### 3. Build and run with Docker Compose

```bash
docker-compose up -d
```

## Maintenance

### Updating the Bot

```bash
# Pull latest changes
git pull

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Restart the service
sudo systemctl restart bubblebot
```

### Troubleshooting

1. **Bot not responding**:
   - Check service status: `sudo systemctl status bubblebot`
   - Check logs: `sudo journalctl -u bubblebot -f`
   - Verify internet connection and API availability

2. **Screenshot errors**:
   - Make sure Playwright is installed correctly: `playwright install --with-deps`
   - Check if you have proper display configuration for headless browsers

3. **API connection issues**:
   - Check if you can reach the API endpoints from your server
   - Verify that your server is not blocking outgoing connections

## Additional Resources

- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [Playwright Python Documentation](https://playwright.dev/python/docs/intro)
- [Bubblemaps Documentation](https://bubblemaps.io) 