import re
import json
from datetime import datetime
from typing import Optional


def parse_amount(text: str) -> Optional[int]:
    cleaned = re.sub(r"[\\s,]", "", text or "")
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def format_amount(value, with_currency: bool = True, sign: str | None = None) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    formatted = f"{number:,.0f}".replace(",", " ")
    if sign in {"+", "-"}:
        formatted = f"{sign}{formatted}"
    return f"{formatted} UZS" if with_currency else formatted


def format_date(date_str: str) -> str:
    if not date_str:
        return "—"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return date_str


def format_datetime(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", ""))
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return dt_str


def clean_text(text, max_len: int = 120) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        try:
            if isinstance(text, dict):
                lines = []
                for key, value in text.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    else:
                        value = "" if value is None else str(value)
                    if key:
                        lines.append(f"{key}\n{value}".strip())
                    elif value:
                        lines.append(str(value))
                text = "\n".join([line for line in lines if line])
            elif isinstance(text, list):
                text = "\n".join([str(item) for item in text if item is not None])
            else:
                text = str(text)
        except Exception:
            text = str(text)
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
