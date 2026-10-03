from abc import ABC, abstractmethod


class TranslationError(Exception):
    pass


class ProviderError(TranslationError):
    pass


class RateLimitError(TranslationError):
    pass


class TimeoutError(TranslationError):
    pass


class AuthenticationError(TranslationError):
    pass


class TranslationProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: str | None = None,
    ) -> str:
        ...