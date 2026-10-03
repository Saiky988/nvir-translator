import logging
from packages.translation.cache import TranslationCache
from packages.translation.providers.base import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    TranslationError,
    TranslationProvider,
)
from packages.translation.schemas import TranslationRequest, TranslationResponse

logger = logging.getLogger("sachitone.engine")


class TranslationEngine:
    def __init__(
        self,
        provider: TranslationProvider,
        cache: TranslationCache | None = None,
        max_length: int = 2000,
    ):
        self.provider = provider
        self.cache = cache or TranslationCache(max_size=1000, enabled=True)
        self.max_length = max_length

    async def execute(self, request: TranslationRequest) -> TranslationResponse:
        normalized_text = request.text.strip()
        if not normalized_text:
            raise TranslationError("Text cannot be empty or blank.")

        if len(normalized_text) > self.max_length:
            raise TranslationError(
                f"Text length ({len(normalized_text)}) exceeds maximum allowed ({self.max_length} characters)."
            )

        source = request.source_language.strip().lower() or "auto"
        target = request.target_language.strip().lower()

        cached_result = self.cache.get(
            text=normalized_text,
            source=source,
            target=target,
            model=self.provider.model_name,
        )
        if cached_result is not None:
            logger.debug("Cache hit for translation to %s", target)
            return TranslationResponse(
                success=True,
                translation=cached_result,
                source_language=source,
                target_language=target,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
            )

        try:
            translation = await self.provider.translate(
                text=normalized_text,
                source_language=source,
                target_language=target,
                context=request.context,
            )
        except (TimeoutError, RateLimitError, AuthenticationError, ProviderError):
            raise
        except Exception as exc:
            logger.error("Engine execution error: %s", type(exc).__name__)
            raise TranslationError("Failed to execute translation.") from exc

        self.cache.set(
            text=normalized_text,
            source=source,
            target=target,
            model=self.provider.model_name,
            translation=translation,
        )

        return TranslationResponse(
            success=True,
            translation=translation,
            source_language=source,
            target_language=target,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
        )