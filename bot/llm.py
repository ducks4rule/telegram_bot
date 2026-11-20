import json
import logging

from bot.schedule import next_week_range

logger = logging.getLogger(__name__)


def _build_category_text(categories: list) -> str:
    lines = []
    for cat in categories:
        if isinstance(cat, dict):
            lines.append(f"- {cat['name']}: {cat.get('description', '')}")
        else:
            lines.append(f"- {cat}")
    return "\n".join(lines)


def build_prompt(source_name: str, text: str, categories: list,
                 start: str, end: str, extract_urls: bool = False) -> str:
    cat_text = _build_category_text(categories)

    fields = [
        '- "title": short event title',
        '- "date": date string (ISO format if possible, or as listed)',
        '- "category": which category it matches',
        '- "venue": venue name if available',
        '- "description": one-sentence summary',
    ]
    if extract_urls:
        fields.append('- "url": direct link to the event page if available, otherwise null')

    fields_text = "\n".join(fields)

    return f"""You are analyzing content from "{source_name}" to find events or items happening between {start} and {end}.

Categories of interest:
{cat_text}

Extract any events, screenings, meetups, concerts, or other items that:
1. Fall within the date range {start} to {end}
2. Match at least one of the categories above based on their description

STRICT RULES:
- Only include items that genuinely fit the category descriptions. Be very selective — quality over quantity.
- EXCLUDE any events that are restricted to FLINTA*, women-only, lesbian-only, or any gender-restricted audience.
- EXCLUDE workshops, courses, or seminars unless they clearly fit a category description.
- If unsure whether something fits, leave it out.

Return a JSON array of objects with these fields:
{fields_text}

If nothing matches, return an empty array: []
Return ONLY valid JSON, no markdown fences or other text.

Content:
{text}"""


async def _call_gemini(prompt: str, config: dict) -> str | None:
    from google import genai

    llm = config["llm"]
    client = genai.Client(api_key=llm["gemini_api_key"])
    response = await client.aio.models.generate_content(
        model=llm["model"], contents=prompt,
    )

    usage = response.usage_metadata
    if usage:
        logger.info("Gemini usage: %d input, %d output tokens",
                     usage.prompt_token_count, usage.candidates_token_count)

    return response.text


async def _call_anthropic(prompt: str, config: dict) -> str | None:
    import anthropic

    llm = config["llm"]
    api_key = llm["anthropic_api_key"]
    logger.debug("Anthropic key: %s...%s", api_key[:8], api_key[-4:])
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=llm["model"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    logger.info("Anthropic usage: %d input, %d output tokens",
                 response.usage.input_tokens, response.usage.output_tokens)

    return response.content[0].text if response.content else None


PROVIDERS = {
    "gemini": _call_gemini,
    "anthropic": _call_anthropic,
}


async def analyze_source(source_name: str, text: str, categories: list,
                         config: dict, extract_urls: bool = False) -> list[dict]:
    schedule = config["schedule"]
    start, end = next_week_range(schedule["timezone"], schedule["lookahead_days"])
    prompt = build_prompt(source_name, text, categories,
                          start.isoformat(), end.isoformat(),
                          extract_urls=extract_urls)

    provider = config["llm"]["provider"]
    call_fn = PROVIDERS.get(provider)
    if not call_fn:
        logger.error("Unknown LLM provider: %s", provider)
        return []

    raw_text = await call_fn(prompt, config)

    if not raw_text:
        logger.warning("Empty LLM response for %s", source_name)
        return []

    try:
        raw = raw_text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        items = json.loads(raw)
        if not isinstance(items, list):
            return []
        return items
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse LLM response for %s", source_name)
        return []
