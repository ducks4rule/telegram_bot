# Telegram Weekly Report Bot

Checks configured websites weekly and sends a Telegram digest of events matching your categories, powered by Gemini Flash.

## Setup

### 1. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, pick a name and username
3. Copy the bot token

### 2. Get Your Chat ID

1. Send any message to your bot
2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `"chat":{"id":XXXXXXX}` in the response

### 3. Get a Gemini API Key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create an API key

### 4. Configure

Copy the example files and fill in your values:

```sh
cp .env.example .env
cp config.example.yaml config.yaml
```

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
GEMINI_API_KEY=your-gemini-key
```

Edit `config.yaml` to add your sources and categories:

```yaml
sources:
  - name: "Local Cinema"
    url: "https://example-cinema.de/programm"
  - name: "Tech Meetup"
    url: "https://meetup.com/some-group/events"

categories:
  - film
  - tech
  - music
```

### 5. Run

```sh
podman-compose up -d
```

## Bot Commands

- `/start` — show help (also shows your chat ID if unauthorized)
- `/report` — generate a report on demand
- `/sources` — list configured sources

## How It Works

1. Fetches each configured URL and extracts readable text
2. Sends the text to Gemini Flash asking for events next week matching your categories
3. Compiles results into a formatted Telegram message
4. Sends automatically every Monday morning (configurable) or on demand via `/report`

## Project Structure

```
├── bot/
│   ├── main.py        # entry point, scheduler
│   ├── config.py      # loads config + env vars
│   ├── scraper.py     # fetch URLs, extract text
│   ├── llm.py         # Gemini API calls
│   ├── report.py      # format the digest message
│   └── telegram.py    # bot commands + scheduled job
├── config.yaml        # sources, categories, schedule
├── .env               # secrets (gitignored)
├── .env.example       # template for .env
├── Containerfile
├── compose.yaml
└── requirements.txt
```
