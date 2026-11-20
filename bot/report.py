from bot.schedule import next_week_range

EMOJIS = [
    "🔥", "🪢", "⛓", "🤘", "🎧", "🎶", "🎬", "💻",
    "🎵", "🎭", "🎉", "🖼", "⚽", "📚", "🍽", "🌍",
    "💡", "🎪", "🧪", "🏠", "✨", "🌙", "🔮", "🎲",
]


def _escape_md(text: str) -> str:
    for char in ("*", "_", "`", "[", "]", "(", ")"):
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

    # single sources first so dedup keeps their entries over aggregator duplicates
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


def format_report(results: dict[str, list[dict]], config: dict) -> str:
    schedule = config["schedule"]
    categories = config["categories"]
    start, end = next_week_range(schedule["timezone"], schedule["lookahead_days"])

    days = schedule["lookahead_days"]
    if days <= 7:
        title = "Weekly Report"
    elif days <= 14:
        title = "2-Week Report"
    else:
        title = "Monthly Report"

    lines = [f"*{title}*"]
    lines.append(f"_{start.strftime('%d.%m.')} — {end.strftime('%d.%m.%Y')}_\n")

    by_cat = _group_by_category(results, config.get("sources", []))

    total = sum(len(items) for items in by_cat.values())
    if total == 0:
        lines.append("Nothing interesting found for next week.")
        return "\n".join(lines)

    for cat, items in by_cat.items():
        emoji = _get_emoji(cat, categories)
        lines.append(f"{emoji} *{_escape_md(cat)}*")
        for item in items:
            date = item.get("date", "?")
            title = item.get("title", "Untitled")
            desc = item.get("description", "")
            url = item.get("url")
            source = item.get("_source", "")

            safe_title = _escape_md(title)
            safe_desc = _escape_md(desc)
            title_text = f"[{safe_title}]({url})" if url else safe_title
            source_tag = f" — {_escape_md(source)}" if source else ""
            lines.append(f"  *{title_text}*")
            lines.append(f"    {date}{source_tag}")
            if safe_desc:
                lines.append(f"    {safe_desc}")
        lines.append("")

    return "\n".join(lines)
