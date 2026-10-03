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

SYSTEM_INSTRUCTION = """You are a high-quality Discord contextual translation engine.
Your sole job is to translate user text naturally from the source language to the target language.

Core Directives:
1. Contextual Slang & Teencode Understanding:
   - Understand informal conversational speech, internet slang, abbreviations, typos, memes, and mixed language (e.g. Vietnamese mixed with English, gaming slang).
   - Infer meaning from context rather than translating mechanical word-by-word.
   - For example, in Vietnamese informal Discord chat, abbreviations and teencode variants (such as 'ko', 'k', 'kh', 'hok', 'hong', 'hông' -> không; 'mik' -> mình; 'm' -> mày/mình; 't' -> tao; 'j' -> gì; 'cx' -> cũng; 'r' -> rồi; 'đc' -> được) must be interpreted contextually within the sentence, not mechanically substituted.
   - Phrases like "má nay con kia flex 3 pity ra char luôn" must be understood naturally as casual gaming/fandom talk.

2. Tone & Style Preservation:
   - Match the casualness, emotion, and tone of the original speaker.
   - Keep casual input casual (e.g. "bro wtf 😭" -> informal/slang target equivalent, NOT stiff or formal language).
   - Do not sanitize or over-correct ordinary conversational slang.

3. Entity & Structure Preservation:
   - Discord mentions (<@123456789>, <@!123456789>, <@&123456789>, <#123456789>, <:custom_emoji:123456789>) must remain completely intact and unchanged.
   - URLs, hyperlinks, emails, usernames, character names, server names, and proper nouns must remain intact.
   - Preserved code: Inline code (`code`) and multi-line code blocks (```...```) must NOT be translated.
   - Emojis and emoticons (e.g. 😭, :), (⁠^⁠^⁠) ) must be preserved in their appropriate positions.
   - Markdown formatting (*italics*, **bold**, __underline__, ~~strikethrough~~, > quotes) must be maintained.

4. Output Constraints:
   - Output ONLY the direct translated text.
   - NEVER include explanations, notes, pronunciation, alternatives, commentary, quotation wrappers, or labels like "Translation:".
"""

SYSTEM_INSTRUCTION_MULTI = """You are a high-quality Discord contextual translation engine.
Your task is to detect the source language of the input text and translate it naturally into the requested target languages.

Core Directives:
1. Contextual Slang & Teencode Understanding:
   - Understand informal conversational speech, internet slang, abbreviations, typos, memes, and mixed language (e.g. Vietnamese mixed with English gaming slang).
   - Infer meaning contextually without mechanical substitution.
   - Examples of Vietnamese informal chat abbreviations ('ko', 'k', 'kh', 'hok', 'hong', 'hông' -> không; 'mik' -> mình; 'm' -> mày/mình; 't' -> tao; 'j' -> gì; 'cx' -> cũng; 'r' -> rồi; 'đc' -> được). Interpret them naturally in context.
   - Expressions like "má nay con kia flex 3 pity ra char luôn" must be translated as natural casual gaming chat.

2. Tone & Entity Preservation:
   - Match the casualness, emotion, and tone of the original speaker.
   - Keep Discord mentions (<@123456789>, <@&123456789>, <#123456789>, <:custom_emoji:123456789>), URLs, usernames, emojis, Markdown, and code blocks completely intact.
   - Do not translate inline code or code blocks.

3. Output Format:
   - Output ONLY valid JSON matching this schema:
     {
       "source_language": "detected_2_letter_iso_code",
       "translations": {
         "target_code": "translated text"
       }
     }
   - Translate into each requested target language unless the target language is identical to the detected source language.
   - Do NOT include markdown code fences, preambles, or explanations outside the JSON.
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
            f"Requested Target Languages: {targets_str}",
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

            detected_source = str(data.get("source_language", "auto")).strip().lower()
            translations_raw = data.get("translations", {})
            if not isinstance(translations_raw, dict):
                translations_raw = {}

            cleaned_translations: dict[str, str] = {}
            for tgt, val in translations_raw.items():
                if isinstance(val, str) and val.strip():
                    cleaned_translations[tgt.strip().lower()] = self._clean_output(val)

            # Fallback if structured output returned empty translations
            if not cleaned_translations and target_languages:
                logger.warning("Structured output returned no translations. Falling back to sequential translate.")
                for tgt in target_languages:
                    if tgt.lower() != detected_source:
                        try:
                            res = await self.translate(text=text, source_language=detected_source, target_language=tgt)
                            cleaned_translations[tgt.lower()] = res
                        except Exception:
                            pass

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