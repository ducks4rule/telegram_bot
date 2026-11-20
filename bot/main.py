import logging

from telegram.ext import ApplicationBuilder, CommandHandler

from bot.config import load_config
from bot.logger import setup_logging
from bot.schedule import get_run_time
from bot.handlers import (
    cmd_start, cmd_report, cmd_sources, cmd_categories,
    cmd_addsource, cmd_addcategory, cmd_removesource, cmd_removecategory,
    scheduled_report,
)

logger = logging.getLogger(__name__)


def main():
    config = load_config()
    setup_logging(config)

    app = ApplicationBuilder().token(config["telegram"]["bot_token"]).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("categories", cmd_categories))
    app.add_handler(CommandHandler("addsource", cmd_addsource))
    app.add_handler(CommandHandler("addcategory", cmd_addcategory))
    app.add_handler(CommandHandler("removesource", cmd_removesource))
    app.add_handler(CommandHandler("removecategory", cmd_removecategory))

    run_time = get_run_time(config)
    app.job_queue.run_daily(
        scheduled_report,
        time=run_time,
        days=(config["schedule"]["day_of_week"],),
        name="weekly_report",
    )

    schedule = config["schedule"]
    logger.info(
        "Bot started. Weekly report scheduled for %s at %s (%s)",
        schedule["day"].capitalize(), schedule["time"], schedule["timezone"],
    )
    app.run_polling()


if __name__ == "__main__":
    main()
