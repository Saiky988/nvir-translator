from fastapi import APIRouter
from packages.translation.schemas import LanguageInfo, LanguagesResponse

router = APIRouter(prefix="/api/v1", tags=["Languages"])

SUPPORTED_LANGUAGES: list[LanguageInfo] = [
    LanguageInfo(code="vi", name="Vietnamese", native_name="Tiếng Việt", flag="🇻🇳"),
    LanguageInfo(code="en", name="English", native_name="English", flag="🇬🇧"),
    LanguageInfo(code="ja", name="Japanese", native_name="日本語", flag="🇯🇵"),
    LanguageInfo(code="ko", name="Korean", native_name="한국어", flag="🇰🇷"),
    LanguageInfo(code="zh", name="Chinese", native_name="中文", flag="🇨🇳"),
    LanguageInfo(code="fr", name="French", native_name="Français", flag="🇫🇷"),
    LanguageInfo(code="de", name="German", native_name="Deutsch", flag="🇩🇪"),
    LanguageInfo(code="es", name="Spanish", native_name="Español", flag="🇪🇸"),
    LanguageInfo(code="ru", name="Russian", native_name="Русский", flag="🇷🇺"),
    LanguageInfo(code="th", name="Thai", native_name="ไทย", flag="🇹🇭"),
    LanguageInfo(code="id", name="Indonesian", native_name="Bahasa Indonesia", flag="🇮🇩"),
]


@router.get("/languages", response_model=LanguagesResponse, summary="List supported languages")
async def list_languages() -> LanguagesResponse:
    return LanguagesResponse(languages=SUPPORTED_LANGUAGES)