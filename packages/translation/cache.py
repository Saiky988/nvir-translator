from collections import OrderedDict


class TranslationCache:
    def __init__(self, max_size: int = 1000, enabled: bool = True):
        self.max_size = max_size
        self.enabled = enabled
        self._store: OrderedDict[tuple[str, str, str, str], str] = OrderedDict()

    def _build_key(self, text: str, source: str, target: str, model: str) -> tuple[str, str, str, str]:
        return (text.strip(), source.strip().lower(), target.strip().lower(), model.strip().lower())

    def get(self, text: str, source: str, target: str, model: str) -> str | None:
        if not self.enabled:
            return None
        key = self._build_key(text, source, target, model)
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, text: str, source: str, target: str, model: str, translation: str) -> None:
        if not self.enabled:
            return
        key = self._build_key(text, source, target, model)
        self._store[key] = translation
        self._store.move_to_end(key)
        if len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()