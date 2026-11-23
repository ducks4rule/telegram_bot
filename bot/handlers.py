import asyncio
import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CONSTANTS, load_config, save_config
from bot.scraper import fetch_and_extract
from bot.llm import analyze_source
from bot.report import format_report

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = CONSTANTS["telegram_max_message_length"]


def _authorized(handler):
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        config = load_config()
        if update.effective_chat.id != config["telegram"]["chat_id"]:
            return
        await handler(update, context, config)
    return wrapper


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


async def _send_message(send_fn, text: str) -> None:
    for chunk in _split_message(text):
        try:
            await send_fn(chunk, parse_mode="Markdown")
        except Exception:
            await send_fn(chunk)


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

    if not extract_urls:
        for item in items:
            item["url"] = urls[0]

    return name, items


def _get_category_name(c) -> str:
    return c["name"] if isinstance(c, dict) else c


def _filter_categories(categories: list, category_filter: str | None,
                       use_defaults: bool, groups: dict, default_group_name: str) -> list:
    if category_filter:
        if category_filter in groups:
            group_names = set(groups[category_filter])
            return [c for c in categories if _get_category_name(c) in group_names]
        return [c for c in categories if _get_category_name(c) == category_filter]

    if use_defaults:
        default_group = groups.get(default_group_name, [])
        if default_group:
            group_names = set(default_group)
            return [c for c in categories if _get_category_name(c) in group_names]
        return categories

    return categories


def _filter_sources(sources: list, active_cat_names: set) -> list:
    filtered = []
    for s in sources:
        source_cats = s.get("categories")
        if source_cats:
            if active_cat_names & set(source_cats):
                filtered.append(s)
        else:
            filtered.append(s)
    return filtered


async def generate_report(config: dict, category_filter: str | None = None,
                          lookahead_days: int | None = None,
                          scheduled: bool = False) -> str:
    all_categories = config["categories"]

    if lookahead_days is not None:
        config = {**config, "schedule": {**config["schedule"], "lookahead_days": lookahead_days}}

    if not all_categories:
        return "No categories configured. Add some via /addcategory."

    use_defaults = category_filter is None
    groups = config.get("category_groups", {})
    default_group_name = config.get("default_group", "default")
    categories = _filter_categories(all_categories, category_filter, use_defaults,
                                    groups, default_group_name)
    if not categories:
        return format_report({}, config)

    active_cat_names = {_get_category_name(c) for c in categories}
    sources = _filter_sources(config["sources"], active_cat_names)

    if not sources:
        return "No sources configured for these categories."

    semaphore = asyncio.Semaphore(config["scraping"]["max_concurrent_requests"])

    async def _throttled(source):
        async with semaphore:
            return await _process_source(source, categories, config)

    tasks = [_throttled(source) for source in sources]
    pairs = await asyncio.gather(*tasks)
    results = {name: items for name, items in pairs}

    found = {name: len(items) for name, items in results.items() if items}
    empty = [name for name, items in results.items() if not items]
    logger.info("Results: %s | Empty: %s", found, empty)

    return format_report(results, config, scheduled=scheduled)


# --- Command handlers ---

@_authorized
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> None:
    args = list(context.args) if context.args else []
    category_filter = None
    lookahead_days = None

    if "month" in args:
        lookahead_days = config["schedule"]["monthly_lookahead_days"]
        args.remove("month")
    if args:
        category_filter = args[0]

    logger.info("Report requested: category=%s, lookahead=%s", category_filter, lookahead_days)
    await update.message.reply_text("Checking sources, one moment...")
    try:
        report = await generate_report(config, category_filter=category_filter,
                                       lookahead_days=lookahead_days)
        await _send_message(update.message.reply_text, report)
    except Exception as e:
        logger.exception("Error generating report")
        await update.message.reply_text(f"⚠️ Error: {e}")


@_authorized
async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> None:
    sources = config["sources"]
    if not sources:
        await update.message.reply_text("No sources configured.")
        return

    lines = ["*Configured sources:*"]
    for s in sources:
        source_type = s.get("type", "single")
        pages = s.get("pages", 1)
        extra = f" [{source_type}]" if source_type != "single" else ""
        if pages > 1:
            extra += f" ({pages} pages)"
        lines.append(f"  • {s['name']}: {s.get('url', ', '.join(s.get('urls', [])))}{extra}")
    await _send_message(update.message.reply_text, "\n".join(lines))


@_authorized
async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> None:
    categories = config["categories"]
    if not categories:
        await update.message.reply_text("No categories configured.")
        return

    lines = ["*Configured categories:*"]
    for c in categories:
        if isinstance(c, dict):
            lines.append(f"  • *{c['name']}*: {c.get('description') or ''}")
        else:
            lines.append(f"  • {c}")
    await _send_message(update.message.reply_text, "\n".join(lines))


@_authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> None:
    await update.message.reply_text(
        "Bot is running.\n\n"
        "*Reports*\n"
        "/report — report for the next week\n"
        "/report month — report for the next month\n"
        "/report <category> — filter by category\n"
        "/report <category> month — combine both\n\n"
        "*Info*\n"
        "/sources — list sources\n"
        "/categories — list categories",
        parse_mode="Markdown",
    )


# --- Scheduled handler (no decorator, no update object) ---

async def scheduled_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    chat_id = config["telegram"]["chat_id"]
    try:
        report = await generate_report(config, scheduled=True)
        send_fn = lambda text, **kwargs: context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        await _send_message(send_fn, report)
    except Exception as e:
        logger.exception("Error in scheduled report")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Scheduled report failed: {e}")
