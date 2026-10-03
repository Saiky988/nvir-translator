import logging
import time
from packages.translation.providers.base import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    TranslationError,
)
from packages.translation.translator import Translator, get_default_translator

logger = logging.getLogger("sachitone.bot.service")

LANGUAGE_FLAGS: dict[str, str] = {
    "vi": "🇻🇳",
    "en": "🇬🇧",
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "zh": "🇨🇳",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "es": "🇪🇸",
    "ru": "🇷🇺",
    "th": "🇹🇭",
    "id": "🇮🇩",
}


class BotRateLimiter:
    def __init__(self, cooldown_seconds: float = 2.0, max_entries: int = 5000):
        self.cooldown = cooldown_seconds
        self.max_entries = max_entries
        self._user_timestamps: dict[int, float] = {}

    def check(self, user_id: int) -> tuple[bool, float]:
        now = time.monotonic()
        if len(self._user_timestamps) > self.max_entries:
            cutoff = now - (self.cooldown * 3)
            self._user_timestamps = {k: v for k, v in self._user_timestamps.items() if v > cutoff}

        last = self._user_timestamps.get(user_id, 0.0)
        elapsed = now - last
        if elapsed < self.cooldown:
            return False, self.cooldown - elapsed

        self._user_timestamps[user_id] = now
        return True, 0.0


class BotTranslatorService:
    def __init__(self, translator: Translator | None = None):
        self.translator = translator or get_default_translator()
        self.rate_limiter = BotRateLimiter(cooldown_seconds=2.0)

    def is_allowed(self, user_id: int) -> tuple[bool, float]:
        return self.rate_limiter.check(user_id)

    def get_flag(self, lang_code: str) -> str:
        return LANGUAGE_FLAGS.get(lang_code.lower(), f"[{lang_code.upper()}]")

    async def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "auto",
        user_id: int | None = None,
        guild_id: int | None = None,
    ) -> tuple[bool, list[str]]:
        if user_id is not None:
            allowed, remaining = self.is_allowed(user_id)
            if not allowed:
                return False, [f"Please wait {remaining:.1f}s before sending another translation request."]

        start_time = time.monotonic()
        try:
            result = await self.translator.translate(
                text=text,
                target_language=target_lang,
                source_language=source_lang,
            )
            elapsed = time.monotonic() - start_time
            logger.info(
                "Translation success | guild_id=%s user_id=%s target=%s latency=%.2fs",
                guild_id,
                user_id,
                target_lang,
                elapsed,
            )
            flag = self.get_flag(result.target_language)
            formatted = f"{flag} {result.translation}"
            chunks = self.split_message(formatted)
            return True, chunks

        except TimeoutError:
            logger.warning("Bot translation timeout | guild_id=%s user_id=%s", guild_id, user_id)
            return False, ["Translation timed out. Please try again in a moment."]

        except RateLimitError:
            logger.warning("Bot upstream rate limit | guild_id=%s user_id=%s", guild_id, user_id)
            return False, ["Service is currently busy with high volume. Please retry in a few seconds."]

        except AuthenticationError:
            logger.error("Bot authentication failure | guild_id=%s", guild_id)
            return False, ["Translation service configuration error. Please contact server admins."]

        except (ProviderError, TranslationError) as exc:
            logger.error("Bot translation error: %s | guild_id=%s", exc, guild_id)
            return False, ["Translation service is temporarily unavailable. Try again in a moment."]

        except Exception as exc:
            logger.error("Bot unhandled translation error: %s | guild_id=%s", type(exc).__name__, guild_id)
            return False, ["An unexpected error occurred while translating. Please try again."]

    @staticmethod
    def split_message(text: str, max_chunk_size: int = 1950) -> list[str]:
        if len(text) <= max_chunk_size:
            return [text]

        chunks: list[str] = []
        lines = text.split("\n")
        current_chunk: list[str] = []
        current_length = 0
        in_code_fence = False
        fence_lang = ""

        for line in lines:
            stripped = line.strip()
            is_fence = stripped.startswith("```")

            if current_length + len(line) + 1 > max_chunk_size and current_chunk:
                if in_code_fence:
                    current_chunk.append("```")
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
                if in_code_fence:
                    current_chunk.append(f"```{fence_lang}")
                    current_length += len(current_chunk[0]) + 1

            if is_fence:
                if in_code_fence:
                    in_code_fence = False
                    fence_lang = ""
                else:
                    in_code_fence = True
                    fence_lang = stripped[3:].strip()

            current_chunk.append(line)
            current_length += len(line) + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks