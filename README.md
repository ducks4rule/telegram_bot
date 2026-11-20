# Telegram Weekly Report Bot

Checks configured websites and sends a Telegram digest of events matching your categories, powered by Gemini Flash.

## Setup

### 1. Create a Telegram Bot

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, pick a name and username
3. Copy the bot token

### 2. Get Your Chat ID

1. Open your new bot in Telegram and press **Start**
2. Send any message (e.g. "hi")
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find `"chat":{"id":XXXXXXX}` in the response

### 3. Get a Gemini API Key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create an API key

### 4. Configure

Copy the example files and fill in your values:

```sh
cp .env.example .env
cp config.example.yaml config.yaml
```

Edit `.env`:

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
GEMINI_API_KEY=your-gemini-key
```

Edit `config.yaml` to add your sources and categories:

```yaml
categories:
  - name: film
    description: "Arthouse, indie, and classic cinema screenings."
  - name: tech
    description: "Software meetups, hackathons, talks about programming."

sources:
  - name: "Local Cinema"
    url: "https://example-cinema.de/programm"
  - name: "Tech Meetup"
    url: "https://meetup.com/some-group/events"
```

### 5. Run

```sh
podman-compose up -d
```

## Deployment

Clone the repo on your server, configure, and start:

```sh
git clone git@github.com:your-user/telegram_bot.git
cd telegram_bot
cp .env.example .env
cp config.example.yaml config.yaml
# edit .env and config.yaml
podman-compose up -d
```

To update:

```sh
cd telegram_bot
git pull
podman-compose up -d --build
```

## Bot Commands

- `/start` — show available commands
- `/report` — generate a report now
- `/report <category>` — report filtered by category
- `/sources` — list configured sources

Only responds to the chat ID configured in `.env`.

## Configuration

### `config.yaml`

| Section | Key | Default | Description |
|---|---|---|---|
| `schedule` | `day` | `monday` | Day of the week for the automatic report |
| `schedule` | `time` | `08:00` | Time (HH:MM) for the automatic report |
| `schedule` | `timezone` | `Europe/Berlin` | Timezone |
| `schedule` | `lookahead_days` | `7` | How many days ahead to look for events |
| `gemini` | `model` | `gemini-2.0-flash` | Gemini model to use |
| `scraping` | `jina` | `true` | Use Jina Reader for JS-heavy pages (falls back to trafilatura) |
| `logging` | `level` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### `.env`

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `GEMINI_API_KEY` | Google Gemini API key |

## How It Works

1. Fetches each configured URL and extracts readable text (via Jina Reader or trafilatura)
2. Sends the text to Gemini Flash with your categories and date range
3. LLM returns matching events as structured JSON
4. Compiles results into a formatted Telegram message
5. Sends automatically on schedule or on demand via `/report`

## Project Structure

```
├── bot/
│   ├── main.py        # entry point, scheduler
│   ├── config.py      # defaults, constants, config loading
│   ├── logger.py      # logging setup
│   ├── schedule.py    # time/date helpers
│   ├── scraper.py     # fetch URLs, extract text
│   ├── llm.py         # Gemini API calls
│   ├── report.py      # format the digest message
│   └── handlers.py    # bot commands + scheduled job
├── config.yaml        # sources, categories, schedule (gitignored)
├── config.example.yaml
├── .env               # secrets (gitignored)
├── .env.example
├── Containerfile
├── compose.yaml
└── requirements.txt
```
