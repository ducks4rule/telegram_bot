from bot.schedule import next_week_range

CATEGORY_EMOJI = {
    "film": "🎬",
    "tech": "💻",
    "music": "🎵",
    "culture": "🎭",
    "party": "🎉",
    "art": "🖼",
    "theater": "🎪",
    "food": "🍽",
    "sport": "⚽",
}


def _escape_md(text: str) -> str:
    for char in ("*", "_", "`", "[", "]", "(", ")"):
        text = text.replace(char, "")
    return text


def _get_emoji(category: str) -> str:
    cat_lower = category.lower()
    for key, emoji in CATEGORY_EMOJI.items():
        if key in cat_lower:
            return emoji
    return "📌"


def format_report(results: dict[str, list[dict]], config: dict) -> str:
    schedule = config["schedule"]
    start, end = next_week_range(schedule["timezone"], schedule["lookahead_days"])

    lines = ["*Weekly Report*"]
    lines.append(f"_{start.strftime('%d.%m.')} — {end.strftime('%d.%m.%Y')}_\n")

    total_items = sum(len(items) for items in results.values())
    if total_items == 0:
        lines.append("Nothing interesting found for next week.")
        return "\n".join(lines)

    for source_name, items in results.items():
        if not items:
            continue
        lines.append(f"*{source_name}*")
        for item in items:
            date = item.get("date", "?")
            title = item.get("title", "Untitled")
            desc = item.get("description", "")
            cat = item.get("category", "")
            url = item.get("url")
            emoji = _get_emoji(cat)

            safe_title = _escape_md(title)
            safe_desc = _escape_md(desc)
            title_text = f"[{safe_title}]({url})" if url else safe_title
            lines.append(f"  {emoji} *{title_text}*")
            lines.append(f"       {date}")
            if safe_desc:
                lines.append(f"       {safe_desc}")
        lines.append("")

    return "\n".join(lines)
