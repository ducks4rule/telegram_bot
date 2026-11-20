from bot.schedule import next_week_range


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
            cat_tag = f" [{cat}]" if cat else ""
            lines.append(f"  • {title}{cat_tag}")
            if desc:
                lines.append(f"    {date} — {desc}")
        lines.append("")

    return "\n".join(lines)
