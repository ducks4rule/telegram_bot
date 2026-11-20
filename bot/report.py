from bot.schedule import next_week_range

EMOJIS = [
    "🔥", "🪢", "⛓", "🤘", "🎧", "🎶", "🎬", "💻",
    "🎵", "🎭", "🎉", "🖼", "⚽", "📚", "🍽", "🌍",
    "💡", "🎪", "🧪", "🏠", "✨", "🌙", "🔮", "🎲",
]


def _escape_md(text: str) -> str:
    for char in ("*", "_", "`", "[", "]"):
        text = text.replace(char, "")
    return text


def _get_emoji(category: str, categories: list) -> str:
    cat_lower = category.lower()
    for c in categories:
        if isinstance(c, dict) and c["name"].lower() == cat_lower:
            idx = c.get("emoji")
            if idx is not None and 0 <= idx < len(EMOJIS):
                return EMOJIS[idx]
    return "•"


def _deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        title = item.get("title", "").lower().strip()
        date = item.get("date", "").strip()
        key = (title, date)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _group_by_category(results: dict[str, list[dict]], sources: list) -> dict[str, list[dict]]:
    source_types = {s["name"]: s.get("type", "single") for s in sources}

    sorted_sources = sorted(
        results.items(),
        key=lambda x: 0 if source_types.get(x[0]) == "single" else 1,
    )

    by_cat = {}
    for source_name, items in sorted_sources:
        for item in items:
            cat = item.get("category", "other")
            item["_source"] = source_name
            by_cat.setdefault(cat, []).append(item)

    for cat in by_cat:
        by_cat[cat] = _deduplicate(by_cat[cat])

    return by_cat


def _period_label(days: int) -> str:
    if days <= 7:
        return "the next week"
    if days <= 14:
        return "the next 2 weeks"
    return "the next month"


def format_report(results: dict[str, list[dict]], config: dict, scheduled: bool = False) -> str:
    schedule = config["schedule"]
    categories = config["categories"]
    start, end = next_week_range(schedule["timezone"], schedule["lookahead_days"])

    period = _period_label(schedule["lookahead_days"])
    heading = "Weekly Report" if scheduled else f"Report for {period}"

    lines = [f"*{heading}*"]
    lines.append(f"_{start.strftime('%d.%m.')} — {end.strftime('%d.%m.%Y')}_\n")

    by_cat = _group_by_category(results, config.get("sources", []))

    total = sum(len(items) for items in by_cat.values())
    if total == 0:
        lines.append(f"Nothing interesting found for {period}.")
        return "\n".join(lines)

    for cat, items in by_cat.items():
        emoji = _get_emoji(cat, categories)
        lines.append(f"{emoji} *{_escape_md(cat)}*\n")

        for item in items:
            item_date = item.get("date", "?")
            item_title = item.get("title", "Untitled")
            item_desc = item.get("description", "")
            item_url = item.get("url")
            item_source = item.get("_source", "")

            safe_title = _escape_md(item_title)
            title_text = f"[{safe_title}]({item_url})" if item_url else safe_title
            source_tag = f" — {_escape_md(item_source)}" if item_source else ""

            lines.append(f"  *{title_text}*")
            lines.append(f"    {item_date}{source_tag}")
            if item_desc:
                lines.append(f"    {_escape_md(item_desc)}")
            lines.append("")

    return "\n".join(lines)
