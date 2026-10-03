from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to translate")
    source_language: str = Field(default="auto", description="Source language ISO code or 'auto'")
    target_language: str = Field(..., min_length=2, max_length=10, description="Target language ISO code")
    context: str | None = Field(default=None, max_length=1000, description="Optional surrounding context")


class TranslationResponse(BaseModel):
    success: bool = True
    translation: str
    source_language: str
    target_language: str
    provider: str = "gemini"
    model: str


class MultiTranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to translate")
    target_languages: list[str] = Field(..., min_length=1, max_length=5, description="Target language codes")
    source_language: str = Field(default="auto", description="Source language ISO code or 'auto'")
    context: str | None = Field(default=None, max_length=1000, description="Optional surrounding context")


class MultiTranslationResponse(BaseModel):
    success: bool = True
    detected_source_language: str
    translations: dict[str, str] = Field(default_factory=dict)
    provider: str = "gemini"
    model: str


class LanguageInfo(BaseModel):
    code: str
    name: str
    native_name: str
    flag: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]