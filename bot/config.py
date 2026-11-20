import os
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

CONSTANTS = {
    "http_timeout": 30,
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "trafilatura_options": {
        "include_links": True,
        "include_tables": True,
    },
    "telegram_max_message_length": 4096,
    "log_format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
}

DEFAULTS = {
    "schedule": {
        "day": "monday",
        "time": "08:00",
        "timezone": "Europe/Berlin",
        "lookahead_days": 7,
        "monthly_lookahead_days": 30,
    },
    "llm": {
        "model": "anthropic/claude-sonnet-4-6",
    },
    "logging": {
        "level": "INFO",
    },
    "scraping": {
        "jina": True,
        "jina_prefix": "https://r.jina.ai/",
        "max_content_length": 50000,
        "max_concurrent_requests": 5,
    },
    "categories": [],
    "sources": [],
}

DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        config = yaml.safe_load(f) or {}

    for section, defaults in DEFAULTS.items():
        if isinstance(defaults, dict):
            config.setdefault(section, {})
            for key, value in defaults.items():
                config[section].setdefault(key, value)
        else:
            config.setdefault(section, defaults)

    config["telegram"] = {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": int(os.environ.get("TELEGRAM_CHAT_ID", "0")),
    }
    config["llm"]["gemini_api_key"] = os.environ.get("GEMINI_API_KEY", "")
    config["llm"]["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")

    model_str = config["llm"]["model"]
    if "/" in model_str:
        provider, model = model_str.split("/", 1)
        config["llm"]["provider"] = provider
        config["llm"]["model"] = model
    else:
        config["llm"]["provider"] = "gemini"

    _validate(config)

    day_name = config["schedule"]["day"].lower()
    if day_name not in DAY_MAP:
        raise ValueError(f"Invalid schedule.day: {day_name}")
    config["schedule"]["day_of_week"] = DAY_MAP[day_name]

    return config


def save_config(config: dict, path: Path = CONFIG_PATH) -> None:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    raw["sources"] = config["sources"]
    raw["categories"] = config["categories"]

    with open(path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _validate(config: dict) -> None:
    if not config["telegram"]["bot_token"]:
        raise ValueError("TELEGRAM_BOT_TOKEN env var is required")
    if not config["telegram"]["chat_id"]:
        raise ValueError("TELEGRAM_CHAT_ID env var is required")

    provider = config["llm"].get("provider", "gemini")
    if provider == "gemini" and not config["llm"]["gemini_api_key"]:
        raise ValueError("GEMINI_API_KEY env var is required when provider is gemini")
    if provider == "anthropic" and not config["llm"]["anthropic_api_key"]:
        raise ValueError("ANTHROPIC_API_KEY env var is required when provider is anthropic")

    time_str = config["schedule"]["time"]
    parts = time_str.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid schedule.time: {time_str} (expected HH:MM)")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid schedule.time: {time_str}")
