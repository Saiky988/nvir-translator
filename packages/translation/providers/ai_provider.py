import asyncio
import json
import logging
import re
from google import genai
from google.genai import types
from google.genai.errors import APIError

from packages.translation.providers.base import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    TranslationProvider,
)

logger = logging.getLogger("sachitone.provider.gemini")

ISO_LANGUAGE_MAP: dict[str, str] = {
    "vietnamese": "vi", "vie": "vi", "vn": "vi", "tiếng việt": "vi",
    "english": "en", "eng": "en", "us": "en", "uk": "en",
    "japanese": "ja", "jpn": "ja", "jp": "ja", "tiếng nhật": "ja",
    "korean": "ko", "kor": "ko", "kr": "ko", "tiếng hàn": "ko",
    "chinese": "zh", "zho": "zh", "chi": "zh", "cn": "zh", "tiếng trung": "zh",
    "spanish": "es", "spa": "es", "tiếng tây ban nha": "es",
    "french": "fr", "fra": "fr", "fre": "fr", "tiếng pháp": "fr",
    "german": "de", "deu": "de", "ger": "de", "tiếng đức": "de",
    "russian": "ru", "rus": "ru", "tiếng nga": "ru",
    "thai": "th", "tha": "th", "tiếng thái": "th",
    "indonesian": "id", "ind": "id", "tiếng indonesia": "id",
    "portuguese": "pt", "por": "pt", "tiếng bồ đào nha": "pt",
    "italian": "it", "ita": "it", "tiếng ý": "it",
}


def normalize_lang_code(code: str) -> str:
    if not code:
        return "auto"
    cleaned = code.strip().lower()
    if cleaned in ISO_LANGUAGE_MAP:
        return ISO_LANGUAGE_MAP[cleaned]
    base = re.split(r"[-_]", cleaned)[0]
    return ISO_LANGUAGE_MAP.get(base, base)


def calculate_reciprocal_targets(source_lang: str, configured_langs: list[str]) -> list[str]:
    norm_source = normalize_lang_code(source_lang)
    norm_configured = [normalize_lang_code(l) for l in configured_langs if l and l.strip()]

    # If source is in configured set, reciprocal targets are the remaining languages
    if norm_source in norm_configured:
        return [l for l in norm_configured if l != norm_source]

    # If source is not in configured set (or unknown/auto), translate into all configured languages
    return norm_configured


SYSTEM_INSTRUCTION = """You are a high-quality Discord contextual translation engine.
Your sole job is to translate user text naturally from the source language to the target language.

Core Directives:
1. Holistic Sentence Interpretation:
   - Interpret the ENTIRE sentence as a coherent whole before translating. Never translate word-by-word or literal tokens.
   - Understand informal conversation, internet slang, abbreviations, omitted subjects, typos, memes, and mixed language based on sentence context.

2. Contextual Vietnamese Teencode & Shorthand:
   - Vietnamese informal Discord messages heavily use abbreviations and teencode. Always determine their meaning from sentence context rather than rigid rules:
     * 'h' frequently means 'giờ' (now/time), e.g. "h lm gì bây giờ" means "giờ làm gì bây giờ" -> "What should I do now?"
     * 'lm' means 'làm' (do/make)
     * 'k', 'ko', 'kh', 'khum', 'hok', 'hong', 'hông' mean 'không' (no/not)
     * 'mik', 'm' mean 'mình' or 'mày' depending on context
     * 't' means 'tao' (I/me), 'j' means 'gì' (what), 'cx' means 'cũng' (also), 'r' means 'rồi' (already)
     * 'đc', 'dc' mean 'được' (can/fine/got it)
     * 'bt' means 'biết' (know) or 'bình thường' (normal) depending on context
     * 's' means 'sao' (why/how), 'v', 'z' mean 'vậy' (so/like that), 'chx' means 'chưa' (not yet)
     * 'mn' means 'mọi người' (everyone), 'ny' means 'người yêu' (partner/lover)
     * 'dt', 'đt' mean 'điện thoại' (phone), 'nt' means 'nhắn tin' (texting)
   - Never assume an abbreviation has one fixed meaning across all contexts (e.g. 'h' in "h lm gì" is 'giờ' (now), but in "mai 2h gặp" it means 'hours').

3. Tone & Intent Preservation:
   - Match the casualness, emotion, slang, sarcasm, and register of the original speaker.
   - Do not sanitize or over-correct informal language. Do not invent missing information.

4. Entity & Structure Preservation:
   - Mentions (<@123>, <#123>, <:emoji:123>), URLs, usernames, server names, proper nouns, and Markdown formatting must remain intact.
   - Inline code (`code`) and multiline code blocks (```code```) must NOT be translated.
   - Emojis must be kept in appropriate contextual positions.

5. Output Format:
   - Output ONLY the raw translation result.
   - Do NOT include labels like "Translation:", notes, or conversational preambles.
"""

SYSTEM_INSTRUCTION_MULTI = """You are a high-quality Discord contextual translation engine.
Your mission is to detect the source language of user messages and provide natural reciprocal translations for a multilingual channel.

Core Directives:
1. Holistic Sentence Interpretation:
   - Interpret the ENTIRE sentence as a whole before translating. Never translate word-by-word.
   - Understand informal conversation, internet slang, abbreviations, typos, memes, and mixed language contextually.

2. Contextual Vietnamese Teencode & Shorthand:
   - Accurately infer Vietnamese abbreviations using sentence context:
     * "h lm gì bây giờ" -> means "giờ làm gì bây giờ" -> "What should I do now?"
     * "hnay mik hok biet lam j" -> "I don't know what to do today"
     * "mai 2h gặp nha mn" -> '2h' is 2 o'clock, 'mn' is everyone -> "See everyone tomorrow at 2 o'clock"
     * "má nay con kia flex 3 pity ra char luôn" -> "Damn, that girl just flexed pulling the character at 3 pity!"
   - Never assume an abbreviation has only one mechanical replacement.

3. Reciprocal Target Language Selection:
   - Detect the source language accurately as a 2-letter ISO 639-1 code (e.g., 'vi', 'en', 'ja', 'es', 'ko', 'zh', 'fr', 'de', 'ru', 'th', 'id', 'pt', 'it').
   - Compare the detected source language against the channel's configured supported languages:
     * If the source language matches one of the configured languages, EXCLUDE it and translate ONLY into the remaining configured languages.
       (Example: In a ['vi', 'en', 'ja'] channel, a Vietnamese message translates ONLY to 'en' and 'ja'. An English message translates ONLY to 'vi' and 'ja'. A Japanese message translates ONLY to 'vi' and 'en'.)
     * If the source language does NOT match any configured language (e.g., Korean 'ko' in a ['vi', 'en', 'ja'] channel), translate into ALL configured languages.
     * NEVER output a translation into the same language as the original input.

4. Output Format:
   - Output ONLY valid JSON matching this schema:
     {
       "source_language": "detected_2_letter_iso_code",
       "translations": {
         "target_code": "translated text"
       }
     }
   - Do NOT include markdown blocks or preambles outside the JSON.
"""


class GeminiProvider(TranslationProvider):
    def __init__(self, api_key: str = "", model_name: str = "gemini-3.5-flash-lite", timeout: float = 15.0):
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout
        self._client: genai.Client | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._api_key:
                raise AuthenticationError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: str | None = None,
    ) -> str:
        client = self._get_client()

        user_prompt_parts = []
        if context:
            user_prompt_parts.append(f"Conversation Context:\n{context}\n")

        source_desc = "Auto-detect" if source_language.lower() == "auto" else source_language
        user_prompt_parts.append(
            f"Source Language: {source_desc}\nTarget Language: {target_language}\nText to Translate:\n{text}"
        )
        prompt = "\n".join(user_prompt_parts)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=config,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or ""
            cleaned = self._clean_output(raw_text)
            if not cleaned:
                raise ProviderError("Gemini returned an empty translation.")
            return cleaned

        except asyncio.TimeoutError as exc:
            logger.warning("Gemini request timed out after %.1fs", self._timeout)
            raise TimeoutError("Translation request timed out.") from exc

        except APIError as exc:
            logger.error("Gemini API error: %s (code: %s)", exc.message, exc.code)
            if exc.code in (400, 401, 403):
                raise AuthenticationError("Gemini authentication failed or invalid key.") from exc
            if exc.code == 429:
                raise RateLimitError("Gemini API rate limit exceeded.") from exc
            raise ProviderError("Gemini service encountered an error.") from exc

        except Exception as exc:
            if isinstance(exc, (TimeoutError, AuthenticationError, RateLimitError, ProviderError)):
                raise
            logger.error("Unexpected error during Gemini translation: %s", type(exc).__name__)
            raise ProviderError("Unexpected translation provider error.") from exc

    async def translate_multiple(
        self,
        text: str,
        target_languages: list[str],
        source_language: str = "auto",
        context: str | None = None,
    ) -> tuple[str, dict[str, str]]:
        client = self._get_client()

        targets_str = ", ".join(target_languages)
        user_prompt_parts = [
            f"Configured Channel Languages: {targets_str}",
            f"Text to Analyze & Translate:\n{text}",
        ]
        if context:
            user_prompt_parts.insert(0, f"Conversation Context:\n{context}\n")
        prompt = "\n".join(user_prompt_parts)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION_MULTI,
            response_mime_type="application/json",
            temperature=0.3,
        )

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=config,
                ),
                timeout=self._timeout,
            )

            raw_text = response.text or ""
            data = self._parse_multi_json(raw_text)

            raw_source = str(data.get("source_language", "auto")).strip().lower()
            detected_source = normalize_lang_code(raw_source)

            expected_targets = calculate_reciprocal_targets(detected_source, target_languages)

            translations_raw = data.get("translations", {})
            if not isinstance(translations_raw, dict):
                translations_raw = {}

            cleaned_translations: dict[str, str] = {}
            for raw_k, val in translations_raw.items():
                if isinstance(val, str) and val.strip():
                    norm_k = normalize_lang_code(raw_k)
                    if norm_k in expected_targets and norm_k != detected_source:
                        cleaned_translations[norm_k] = self._clean_output(val)

            missing_expected = [t for t in expected_targets if t not in cleaned_translations]
            if missing_expected:
                for tgt in missing_expected:
                    try:
                        res = await self.translate(
                            text=text,
                            source_language=detected_source,
                            target_language=tgt,
                            context=context,
                        )
                        if res and res.strip():
                            cleaned_translations[tgt] = res.strip()
                    except Exception as err:
                        logger.warning("Fallback translate for %s failed: %s", tgt, err)

            return detected_source, cleaned_translations

        except asyncio.TimeoutError as exc:
            logger.warning("Gemini multi-translate timed out after %.1fs", self._timeout)
            raise TimeoutError("Translation request timed out.") from exc

        except APIError as exc:
            logger.error("Gemini API error in multi-translate: %s (code: %s)", exc.message, exc.code)
            if exc.code in (400, 401, 403):
                raise AuthenticationError("Gemini authentication failed.") from exc
            if exc.code == 429:
                raise RateLimitError("Gemini API rate limit exceeded.") from exc
            raise ProviderError("Gemini service encountered an error.") from exc

        except Exception as exc:
            if isinstance(exc, (TimeoutError, AuthenticationError, RateLimitError, ProviderError)):
                raise
            logger.error("Unexpected error in multi-translate: %s", type(exc).__name__)
            raise ProviderError("Unexpected translation provider error.") from exc

    def _parse_multi_json(self, text: str) -> dict:
        cleaned = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
        else:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]

        try:
            return json.loads(cleaned)
        except Exception as exc:
            logger.warning("Failed to parse Gemini JSON output: %s (Raw: %s)", exc, text[:150])
            return {"source_language": "auto", "translations": {}}

    def _clean_output(self, text: str) -> str:
        cleaned = text.strip()
        prefixes_to_strip = ["Translation:", "translation:"]
        for prefix in prefixes_to_strip:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("“") and cleaned.endswith("”")
        ):
            if cleaned.count('"') == 2 or (cleaned.count("“") == 1 and cleaned.count("”") == 1):
                cleaned = cleaned[1:-1].strip()
        return cleaned
