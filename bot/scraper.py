import logging

import httpx
import trafilatura

from bot.config import CONSTANTS

logger = logging.getLogger(__name__)


async def _fetch_via_jina(url: str, jina_prefix: str) -> str | None:
    jina_url = f"{jina_prefix}{url}"
    async with httpx.AsyncClient(timeout=CONSTANTS["http_timeout"], follow_redirects=True) as client:
        resp = await client.get(jina_url, headers={"Accept": "text/markdown"})
        resp.raise_for_status()
    text = resp.text.strip()
    return text if text else None


async def _fetch_via_trafilatura(url: str) -> str | None:
    async with httpx.AsyncClient(timeout=CONSTANTS["http_timeout"], follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": CONSTANTS["user_agent"]})
        resp.raise_for_status()
    return trafilatura.extract(resp.text, **CONSTANTS["trafilatura_options"])


async def fetch_and_extract(url: str, scraping_config: dict) -> str | None:
    max_length = scraping_config["max_content_length"]

    if scraping_config["jina"]:
        try:
            text = await _fetch_via_jina(url, scraping_config["jina_prefix"])
            if text:
                return text[:max_length]
        except httpx.HTTPError as e:
            logger.warning("Jina failed for %s: %s, falling back to trafilatura", url, e)

    try:
        text = await _fetch_via_trafilatura(url)
        if text:
            return text[:max_length]
    except httpx.HTTPError as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None

    return None
