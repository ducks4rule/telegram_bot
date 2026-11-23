# Telegram Weekly Report Bot

Checks configured websites and sends a Telegram digest of events matching your categories. Supports multiple LLM providers (Anthropic, Gemini).

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

### 3. Get an LLM API Key

Either:
- **Anthropic**: get a key at [console.anthropic.com](https://console.anthropic.com/)
- **Gemini**: get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 4. Configure

```sh
cp .env.example .env
cp config.example.yaml config.yaml
cp prompt_rules.example.yaml prompt_rules.yaml
```

Edit `.env` with your secrets. Edit `config.yaml` with your sources, categories, and schedule. Edit `prompt_rules.yaml` with your LLM filtering rules.

### 5. Run

```sh
podman-compose up -d
```

## Deployment

```sh
git clone git@github.com:your-user/telegram_bot.git
cd telegram_bot
cp .env.example .env
cp config.example.yaml config.yaml
cp prompt_rules.example.yaml prompt_rules.yaml
# edit all three files
podman-compose up -d
```

To update:

```sh
cd telegram_bot
git pull && podman-compose down && podman-compose up -d --build
```

## Bot Commands

- `/start`, `/help` — show available commands
- `/report` — report for the next week (default categories)
- `/report month` — report for the next month
- `/report <category>` — filter by single category
- `/report <group>` — filter by category group (e.g. `party`)
- `/report <category> month` — combine both
- `/sources` — list configured sources
- `/categories` — list configured categories

Only responds to the chat ID configured in `.env`.

## Configuration

### `config.yaml`

| Section | Key | Default | Description |
|---|---|---|---|
| `schedule` | `day` | `monday` | Day of the week for the automatic report |
| `schedule` | `time` | `08:00` | Time (HH:MM) for the automatic report |
| `schedule` | `timezone` | `Europe/Berlin` | Timezone |
| `schedule` | `lookahead_days` | `7` | Days ahead for weekly report |
| `schedule` | `monthly_lookahead_days` | `30` | Days ahead for `/report month` |
| `llm` | `model` | `anthropic/claude-sonnet-4-6` | LLM model (`provider/model` format) |
| `llm` | `max_tokens` | `4096` | Max output tokens per LLM call |
| `scraping` | `jina` | `true` | Use Jina Reader (falls back to trafilatura) |
| `scraping` | `max_content_length` | `50000` | Max chars per scraped page |
| `scraping` | `max_concurrent_requests` | `5` | Concurrent source fetches |
| `logging` | `level` | `INFO` | Log level |
| `default_group` | | `default` | Which category group to use for `/report` |

#### Sources

```yaml
sources:
  - name: "My Venue"
    url: "https://venue.at/events"
    # type: "single" (default) — links to source URL
    # type: "aggregator" — LLM extracts per-event links

  - name: "Paginated Site"
    url: "https://site.at/events?page={page}"
    pages: 5
    type: "aggregator"

  - name: "Multi URL"
    urls:
      - "https://site.at/concerts"
      - "https://site.at/parties"

  - name: "Category-specific Source"
    url: "https://metal.at/events"
    type: "aggregator"
    categories: [heavy-music]  # only checked for these categories
```

#### Categories

```yaml
# emoji index: 0🔥 1🪢 2⛓ 3🤘 4🎧 5🎶 6🎬 7💻 8🎵 9🎭 10🎉 11🖼
categories:
  - name: music
    emoji: 8
    description: "Jazz, electronic, and experimental music."
```

#### Category Groups

```yaml
default_group: "default"

category_groups:
  default: [music, film]
  party: [electronic, heavy-music]
  all: [music, film, electronic, heavy-music]
```

### `.env`

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `GEMINI_API_KEY` | Google Gemini API key (if using Gemini) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Anthropic) |
| `ANTHROPIC_BASE_URL` | Custom base URL for Anthropic (e.g. Azure Foundry) |

### `prompt_rules.yaml`

LLM filtering rules. Gitignored — copy from `prompt_rules.example.yaml` and customize:

```yaml
rules:
  - "Only include items that genuinely fit the category descriptions."
  - "EXCLUDE sold out events."
  - "If unsure whether something fits, leave it out."
```

## How It Works

1. Fetches each configured URL and extracts readable text (via Jina Reader or trafilatura)
2. Sends the text to the configured LLM with your categories, date range, and prompt rules
3. LLM returns matching events as structured JSON
4. Deduplicates, groups by category, sorts by date
5. Sends automatically on schedule or on demand via `/report`

## Project Structure

```
├── bot/
│   ├── main.py        # entry point, scheduler
│   ├── config.py      # defaults, constants, config loading
│   ├── logger.py      # logging setup
│   ├── schedule.py    # time/date helpers
│   ├── scraper.py     # fetch URLs, extract text
│   ├── llm.py         # LLM provider calls (Anthropic, Gemini)
│   ├── report.py      # format the digest message
│   └── handlers.py    # bot commands + scheduled job
├── config.yaml              # sources, categories, schedule (gitignored)
├── config.example.yaml
├── prompt_rules.yaml        # LLM filtering rules (gitignored)
├── prompt_rules.example.yaml
├── .env                     # secrets (gitignored)
├── .env.example
├── Containerfile
├── compose.yaml
└── requirements.txt
```
