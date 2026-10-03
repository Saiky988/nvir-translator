from functools import lru_cache
from config.settings import settings
from packages.translation.cache import TranslationCache
from packages.translation.engine import TranslationEngine
from packages.translation.providers.ai_provider import GeminiProvider
from packages.translation.providers.base import TranslationProvider
from packages.translation.schemas import (
    MultiTranslationRequest,
    MultiTranslationResponse,
    TranslationRequest,
    TranslationResponse,
)


class Translator:
    def __init__(self, engine: TranslationEngine):
        self.engine = engine

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
        context: str | None = None,
    ) -> TranslationResponse:
        request = TranslationRequest(
            text=text,
            source_language=source_language,
            target_language=target_language,
            context=context,
        )
        return await self.engine.execute(request)

    async def translate_multiple(
        self,
        text: str,
        target_languages: list[str],
        source_language: str = "auto",
        context: str | None = None,
    ) -> MultiTranslationResponse:
        request = MultiTranslationRequest(
            text=text,
            target_languages=target_languages,
            source_language=source_language,
            context=context,
        )
        return await self.engine.execute_multi(request)


@lru_cache
def get_default_translator() -> Translator:
    provider: TranslationProvider = GeminiProvider(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
        timeout=settings.translation_timeout,
    )
    cache = TranslationCache(max_size=1000, enabled=True)
    engine = TranslationEngine(
        provider=provider,
        cache=cache,
        max_length=settings.max_translation_length,
    )
    return Translator(engine=engine)