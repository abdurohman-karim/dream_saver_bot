import json
from pathlib import Path
from threading import Lock


class RegistrationStore:
    def __init__(self, path: str = "data/registrations.json"):
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

    def is_registered(self, tg_user_id: int) -> bool:
        return bool(self._data.get(str(tg_user_id)))

    def set_registered(self, tg_user_id: int, value: bool = True) -> None:
        self._data[str(tg_user_id)] = bool(value)
        self._save()


store = RegistrationStore()
