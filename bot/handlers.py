import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CONSTANTS, load_config, save_config
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


def _expand_urls(source: dict) -> list[str]:
    urls = source.get("urls", [])
    url = source.get("url", "")
    pages = source.get("pages", 1)

    if urls:
        return urls
    if pages > 1 and "{page}" in url:
        return [url.replace("{page}", str(p)) for p in range(1, pages + 1)]
    return [url] if url else []


async def _process_source(source: dict, categories: list, config: dict) -> tuple[str, list[dict]]:
    name = source["name"]
    urls = _expand_urls(source)
    source_type = source.get("type", "single")
    extract_urls = source_type == "aggregator"

    if not urls:
        logger.warning("Skipping %s: no URLs configured", name)
        return name, []

    logger.info("Checking %s (%d URLs)", name, len(urls))

    texts = []
    for url in urls:
        text = await fetch_and_extract(url, config["scraping"])
        if text:
            texts.append(text)

    if not texts:
        logger.warning("Skipping %s: no content extracted", name)
        return name, []

    combined = "\n\n".join(texts)
    items = await analyze_source(name, combined, categories, config, extract_urls=extract_urls)
    for item in items:
        if not extract_urls:
            item["url"] = urls[0]
    return name, items


async def generate_report(config: dict, category_filter: str | None = None,
                          lookahead_days: int | None = None) -> str:
    sources = config["sources"]
    categories = config["categories"]

    if lookahead_days:
        config = {**config, "schedule": {**config["schedule"], "lookahead_days": lookahead_days}}

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
        try:
            await send_fn(chunk, parse_mode="Markdown")
        except Exception:
            await send_fn(chunk)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    args = list(context.args) if context.args else []
    category_filter = None
    lookahead_days = None

    if "month" in args:
        lookahead_days = 30
        args.remove("month")
    if args:
        category_filter = args[0]

    await update.message.reply_text("Checking sources, one moment...")
    try:
        report = await generate_report(config, category_filter=category_filter,
                                       lookahead_days=lookahead_days)
        await _send_report(update.message.reply_text, report)
    except Exception as e:
        logger.exception("Error generating report")
        await update.message.reply_text(f"⚠️ Error: {e}")


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
        "Bot is running.\n\n"
        "*Reports*\n"
        "/report — generate a report now\n"
        "/report <category> — filter by category\n\n"
        "*Config*\n"
        "/sources — list sources\n"
        "/categories — list categories\n"
        "/addsource <name> <url> [aggregator]\n"
        "/addcategory <name> <description>\n"
        "/removesource <name>\n"
        "/removecategory <name>",
        parse_mode="Markdown",
    )


async def cmd_addsource(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /addsource <name> <url> [aggregator]\n"
            "Example: /addsource \"Local Cinema\" https://cinema.at/programm aggregator"
        )
        return

    text = " ".join(args)
    source_type = "single"
    if text.rstrip().endswith(" aggregator"):
        source_type = "aggregator"
        text = text.rsplit(" aggregator", 1)[0]

    parts = text.rsplit(" ", 1)
    if len(parts) != 2 or not parts[1].startswith("http"):
        await update.message.reply_text("Could not parse. Put the URL last:\n/addsource My Source https://example.com")
        return

    name, url = parts[0], parts[1]

    for s in config["sources"]:
        if s["url"] == url:
            await update.message.reply_text(f"Source with URL {url} already exists.")
            return

    source = {"name": name, "url": url}
    if source_type == "aggregator":
        source["type"] = "aggregator"

    config["sources"].append(source)
    save_config(config)
    await update.message.reply_text(f"Added: {name} ({url}) [{source_type}]")


async def cmd_addcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /addcategory <name> <description>\n"
            "Example: /addcategory music Jazz, electronic, and experimental music"
        )
        return

    name = context.args[0]
    description = " ".join(context.args[1:]) if len(context.args) > 1 else ""

    for c in config["categories"]:
        cat_name = c["name"] if isinstance(c, dict) else c
        if cat_name == name:
            await update.message.reply_text(f"Category '{name}' already exists.")
            return

    category = {"name": name, "description": description} if description else name
    config["categories"].append(category)
    save_config(config)
    await update.message.reply_text(f"Added category: {name}" + (f"\n{description}" if description else ""))


async def cmd_removesource(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removesource <name>")
        return

    name = " ".join(context.args)
    original_len = len(config["sources"])
    config["sources"] = [s for s in config["sources"] if s["name"] != name]

    if len(config["sources"]) == original_len:
        await update.message.reply_text(f"Source '{name}' not found.")
        return

    save_config(config)
    await update.message.reply_text(f"Removed source: {name}")


async def cmd_removecategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removecategory <name>")
        return

    name = " ".join(context.args)
    original_len = len(config["categories"])
    config["categories"] = [
        c for c in config["categories"]
        if (c["name"] if isinstance(c, dict) else c) != name
    ]

    if len(config["categories"]) == original_len:
        await update.message.reply_text(f"Category '{name}' not found.")
        return

    save_config(config)
    await update.message.reply_text(f"Removed category: {name}")


async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if not is_authorized(update.effective_chat.id, config):
        return

    categories = config["categories"]
    if not categories:
        await update.message.reply_text("No categories configured.")
        return

    lines = ["*Configured categories:*"]
    for c in categories:
        if isinstance(c, dict):
            lines.append(f"  • *{c['name']}*: {c.get('description', '')}")
        else:
            lines.append(f"  • {c}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def scheduled_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    chat_id = config["telegram"]["chat_id"]
    try:
        report = await generate_report(config)
        for chunk in _split_message(report):
            try:
                await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
    except Exception as e:
        logger.exception("Error in scheduled report")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Scheduled report failed: {e}")
