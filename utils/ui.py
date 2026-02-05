import re
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


def clean_text(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
