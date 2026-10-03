import logging
from fastapi import APIRouter, Depends, HTTPException, status
from apps.api.dependencies import get_translator
from packages.translation.providers.base import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    TranslationError,
)
from packages.translation.schemas import TranslationRequest, TranslationResponse
from packages.translation.translator import Translator

logger = logging.getLogger("sachitone.api.translate")
router = APIRouter(prefix="/api/v1", tags=["Translation"])


@router.post(
    "/translate",
    response_model=TranslationResponse,
    summary="Translate text",
    description="Translates input text contextually using the configured translation engine.",
    responses={
        400: {"description": "Invalid input text or parameters"},
        429: {"description": "Provider rate limit reached"},
        502: {"description": "Provider upstream error"},
        503: {"description": "Service unavailable or misconfigured"},
        504: {"description": "Translation request timed out"},
    },
)
async def translate_text(
    payload: TranslationRequest,
    translator: Translator = Depends(get_translator),
) -> TranslationResponse:
    try:
        return await translator.translate(
            text=payload.text,
            target_language=payload.target_language,
            source_language=payload.source_language,
            context=payload.context,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Translation request timed out.") from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upstream translation rate limit reached. Please retry later.",
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation service configuration error.",
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream AI provider error occurred.",
        ) from exc
    except TranslationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unhandled translation route error: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred.",
        ) from exc