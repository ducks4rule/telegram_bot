import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CONSTANTS, load_config
from bot.scraper import fetch_and_extract
from bot.llm import analyze_source
from bot.report import format_report

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = CONSTANTS["telegram_max_message_length"]


def is_authorized(chat_id: int, config: dict) -> bool:
    return chat_id == config["telegram"]["chat_id"]


def _split_message(text: str) -> list[str]:
    if len(text) <= TELEGRAM_MAX_LENGTH:
        return [text]

    messages = []
    while text:
        if len(text) <= TELEGRAM_MAX_LENGTH:
            messages.append(text)
            break
        split_at = text.rfind("\n", 0, TELEGRAM_MAX_LENGTH)
        if split_at == -1:
            split_at = TELEGRAM_MAX_LENGTH
        messages.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return messages


async def _process_source(source: dict, categories: list, config: dict) -> tuple[str, list[dict]]:
    name = source["name"]
    url = source["url"]
    logger.info("Checking %s (%s)", name, url)

    text = await fetch_and_extract(url, config["scraping"])
    if text:
        items = await analyze_source(name, text, categories, config)
        return name, items

    logger.warning("Skipping %s: no content extracted", name)
    return name, []


async def generate_report(config: dict, category_filter: str | None = None) -> str:
    sources = config["sources"]
    categories = config["categories"]

    if not categories:
        return "No categories configured. Add some to config.yaml."

    if category_filter:
        categories = [c for c in categories
                      if (c["name"] if isinstance(c, dict) else c) == category_filter]
        if not categories:
            return format_report({}, config)

    if not sources:
        return "No sources configured. Add some to config.yaml."

    tasks = [_process_source(source, categories, config) for source in sources]
    pairs = await asyncio.gather(*tasks)
    results = {name: items for name, items in pairs}

    return format_report(results, config)


async def _send_report(send_fn, report: str) -> None:
    for chunk in _split_message(report):
        await send_fn(chunk, parse_mode="Markdown")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    category_filter = context.args[0] if context.args else None
    await update.message.reply_text("Checking sources, one moment...")
    report = await generate_report(config, category_filter=category_filter)
    await _send_report(update.message.reply_text, report)


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    sources = config["sources"]
    if not sources:
        await update.message.reply_text("No sources configured.")
        return

    lines = ["*Configured sources:*"]
    for s in sources:
        lines.append(f"  • {s['name']}: {s['url']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    await update.message.reply_text(
        "Bot is running.\n"
        "/report — generate a report now\n"
        "/report <category> — filter by category\n"
        "/sources — list configured sources"
    )


async def scheduled_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    chat_id = config["telegram"]["chat_id"]
    report = await generate_report(config)
    for chunk in _split_message(report):
        await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
