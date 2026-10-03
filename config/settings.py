import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    discord_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    api_host: str = "0.0.0.0"
    api_port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    )
    bot_prefix: str = "!"
    log_level: str = "INFO"
    max_translation_length: int = 2000
    translation_timeout: float = 15.0

    database_path: str = Field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "data/translator.db")
    )
    auto_translate_max_targets: int = 3
    auto_translate_semaphore: int = 5
    embed_color: int = 0x5865F2


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def setup_logging() -> None:
    numeric_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )