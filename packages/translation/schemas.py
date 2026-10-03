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


class LanguageInfo(BaseModel):
    code: str
    name: str
    native_name: str
    flag: str


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]