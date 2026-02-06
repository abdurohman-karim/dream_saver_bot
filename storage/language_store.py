import json
from pathlib import Path
from threading import Lock


class LanguageStore:
    def __init__(self, path: str = "data/languages.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        with self._lock:
            self.path.write_text(json.dumps(self._data), encoding="utf-8")

    def get(self, tg_user_id: int) -> str | None:
        return self._data.get(str(tg_user_id))

    def set(self, tg_user_id: int, language: str) -> None:
        self._data[str(tg_user_id)] = language
        self._save()


store = LanguageStore()
