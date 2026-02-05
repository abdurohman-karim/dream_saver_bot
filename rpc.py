# rpc.py
import httpx
import logging
from config import RPC_URL, RPC_TOKEN, TELEGRAM_REGISTER_URL, TELEGRAM_STATUS_URL


class RPCError(RuntimeError):
    """
    Ошибка прикладного уровня (jsonrpc.error).
    """

    def __init__(self, error: dict):
        self.error = error
        message = error.get("message") or "RPC error"
        code = error.get("code")
        super().__init__(f"{message} (code={code})")


class RPCTransportError(RuntimeError):
    """
    Ошибка сети / HTTP.
    """


class RegistrationError(RuntimeError):
    """
    Ошибка регистрации телефона.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) <= 4:
        return "***"
    return f"+***{digits[-4:]}"


async def rpc(method: str, params: dict | None = None) -> dict:
    """
    Универсальный вызов JSON-RPC.
    Возвращает УЖЕ result (а не весь JSON-RPC объект).
    В случае ошибки бросает RPCError / RPCTransportError.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                RPC_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {RPC_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as e:
        logging.exception("RPC transport error")
        raise RPCTransportError(str(e))

    if resp.status_code >= 400:
        # пробуем понять, это JSON-RPC ошибка или реально транспорт
        try:
            data = resp.json()
        except ValueError:
            # не JSON – реально что-то сломалось (HTML, nginx и т.п.)
            logging.error("RPC HTTP %s non-json body: %s", resp.status_code, resp.text)
            raise RPCTransportError(f"HTTP {resp.status_code}")

        if "error" in data and data["error"]:
            logging.error("RPC logical error: %s", data["error"])
            # ← вернём как прикладную ошибку
            raise RPCError(data["error"])

        # fallback
        logging.error("RPC HTTP %s unknown error: %s", resp.status_code, resp.text)
        raise RPCTransportError(f"HTTP {resp.status_code}")

    data = resp.json()
    logging.debug("RPC %s → %s", method, data)

    if "error" in data and data["error"]:
        raise RPCError(data["error"])

    # result может отсутствовать (если сервер так сделал),
    # тогда вернём весь data — но твой бекенд всегда даёт result.
    return data.get("result") or data


async def telegram_register(tg_user_id: int, phone: str, name: str | None = None) -> dict:
    payload = {
        "tg_user_id": tg_user_id,
        "phone": phone,
        "name": name,
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                TELEGRAM_REGISTER_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {RPC_TOKEN}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
    except httpx.RequestError as e:
        logging.exception("Registration transport error")
        raise RPCTransportError(str(e))

    try:
        data = resp.json()
    except ValueError:
        logging.error(
            "Registration non-json response: status=%s body=%s payload={tg_user_id=%s, phone=%s}",
            resp.status_code,
            resp.text[:2000],
            tg_user_id,
            _mask_phone(phone),
        )
        raise RPCTransportError(f"HTTP {resp.status_code}")

    if resp.status_code >= 400 or data.get("status") == "error":
        code = data.get("code") or "registration_failed"
        message = data.get("message") or "Registration failed"
        logging.error(
            "Registration error: status=%s code=%s message=%s payload={tg_user_id=%s, phone=%s}",
            resp.status_code,
            code,
            message,
            tg_user_id,
            _mask_phone(phone),
        )
        raise RegistrationError(code, message)

    return data


async def telegram_status(tg_user_id: int) -> bool:
    payload = {"tg_user_id": tg_user_id}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                TELEGRAM_STATUS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {RPC_TOKEN}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
    except httpx.RequestError as e:
        logging.exception("Registration status transport error")
        raise RPCTransportError(str(e))

    try:
        data = resp.json()
    except ValueError:
        logging.error(
            "Registration status non-json response: status=%s body=%s payload={tg_user_id=%s}",
            resp.status_code,
            resp.text[:2000],
            tg_user_id,
        )
        raise RPCTransportError(f"HTTP {resp.status_code}")

    if resp.status_code >= 400 or data.get("status") != "ok":
        logging.error(
            "Registration status error: status=%s body=%s payload={tg_user_id=%s}",
            resp.status_code,
            data,
            tg_user_id,
        )
        raise RPCTransportError(f"HTTP {resp.status_code}")

    return bool(data.get("registered"))
