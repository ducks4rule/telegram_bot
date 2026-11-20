import logging

from bot.config import CONSTANTS


def setup_logging(config: dict) -> None:
    level_name = config["logging"]["level"].upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        format=CONSTANTS["log_format"],
        level=level,
    )
