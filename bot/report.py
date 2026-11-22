from datetime import date, datetime

from datetime import datetime

from bot.schedule import next_week_range

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

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
    if not category:
        return "•"
    cat_lower = category.lower()
    for c in categories:
        if isinstance(c, dict) and c["name"].lower() == cat_lower:
            idx = c.get("emoji")
            if idx is not None and 0 <= idx < len(EMOJIS):
                return EMOJIS[idx]
    return "•"


def _format_date(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        weekday = WEEKDAYS[d.weekday()]
        return f"{weekday} {d.strftime('%d.%m.%Y')}"
    except (ValueError, IndexError):
        return date_str


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    for char in "–—-:,.'\"!?()[]":
        t = t.replace(char, " ")
    words = sorted(set(t.split()))
    return " ".join(words)


def _deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        title = _normalize_title(item.get("title") or "")
        date = (item.get("date") or "").strip()[:10]
        venue = (item.get("venue") or "").lower().split(",")[0].split("/")[0].strip()
        key = (date, venue)
        if key and key in seen and title:
            already = [_normalize_title(u.get("title") or "") for u in unique
                       if (u.get("date") or "").strip()[:10] == date]
            if any(_titles_match(title, existing) for existing in already):
                continue
        seen.add(key)
        unique.append(item)
    return unique


def _titles_match(a: str, b: str) -> bool:
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return False
    overlap = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(overlap) >= max(1, smaller * 0.5)


def _group_by_category(results: dict[str, list[dict]], sources: list) -> dict[str, list[dict]]:
    source_types = {s["name"]: s.get("type", "single") for s in sources}

    sorted_sources = sorted(
        results.items(),
        key=lambda x: 0 if source_types.get(x[0]) == "single" else 1,
    )

    by_cat = {}
    for source_name, items in sorted_sources:
        for item in items:
            cat = item.get("category") or "other"
            item["_source"] = source_name
            by_cat.setdefault(cat, []).append(item)

    for cat in by_cat:
        by_cat[cat] = _deduplicate(by_cat[cat])
        by_cat[cat].sort(key=lambda item: item.get("date") or "9999")

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

        grouped = {}
        for item in items:
            date = item.get("date") or "?"
            venue = item.get("venue") or ""
            key = (date, venue)
            grouped.setdefault(key, []).append(item)

        for (raw_date, venue), group in grouped.items():
            formatted_date = _format_date(raw_date)
            venue_tag = f" @ {_escape_md(venue)}" if venue else ""
            lines.append(f"  *{formatted_date}{venue_tag}*")

            for item in group:
                item_title = item.get("title") or "Untitled"
                item_desc = item.get("description") or ""
                item_url = item.get("url")
                item_source = item.get("_source") or ""

                safe_title = _escape_md(item_title)
                title_text = f"[{safe_title}]({item_url})" if item_url else safe_title
                source_tag = f" ({_escape_md(item_source)})" if item_source else ""

                lines.append(f"    {title_text}{source_tag}")
                if item_desc:
                    lines.append(f"      {_escape_md(item_desc)}")
            lines.append("")

    return "\n".join(lines)
