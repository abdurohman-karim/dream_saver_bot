import json
from pathlib import Path
from threading import Lock


class CurrencyStore:
    def __init__(self, path: str = "data/currencies.json"):
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
            self.path.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")

    def get(self, tg_user_id: int) -> dict | None:
        value = self._data.get(str(tg_user_id))
        return value if isinstance(value, dict) else None

    def set(self, tg_user_id: int, currency: dict | None) -> None:
        key = str(tg_user_id)
        if currency is None:
            self._data.pop(key, None)
        else:
            self._data[key] = currency
        self._save()


store = CurrencyStore()
