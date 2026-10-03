import multiprocessing
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.main import app
from apps.bot.main import main as run_bot
from config.settings import settings

__all__ = ["app"]


def start_api():
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


def start_bot():
    run_bot()


if __name__ == "__main__":
    p_api = multiprocessing.Process(target=start_api, name="FastAPI-Process")
    p_bot = multiprocessing.Process(target=start_bot, name="DiscordBot-Process")

    p_api.start()
    p_bot.start()

    p_api.join()
    p_bot.join()
