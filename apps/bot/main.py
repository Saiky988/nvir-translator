import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.bot.client import SachitoneBot
from config.settings import settings, setup_logging

logger = logging.getLogger("sachitone.bot")


def main() -> None:
    setup_logging()
    logger.info("Initializing Sachitone Translator Bot v1.0.0")

    if not settings.discord_token:
        logger.critical("DISCORD_TOKEN is missing. Provide it in .env or the environment.")
        sys.exit(1)

    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY is not set. Translations will fail until it is provided.")

    bot = SachitoneBot()
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()