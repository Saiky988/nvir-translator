from config.settings import Settings, get_settings
from packages.translation.translator import Translator, get_default_translator


def get_app_settings() -> Settings:
    return get_settings()


def get_translator() -> Translator:
    return get_default_translator()