import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.routes import health, languages, translate
from config.settings import settings, setup_logging

logger = logging.getLogger("sachitone.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Sachitone Translator API starting up on %s:%d", settings.api_host, settings.api_port)
    yield
    logger.info("Sachitone Translator API shutting down")


app = FastAPI(
    title="Sachitone Translator API",
    version="1.0.0",
    description="Contextual Discord AI translation bot and HTTP API powered by Gemini",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(translate.router)
app.include_router(languages.router)


@app.get("/", summary="API Root", tags=["General"])
async def root() -> dict[str, str]:
    return {
        "name": "Sachitone Translator API",
        "version": "1.0.0",
        "status": "online",
    }


def run() -> None:
    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()