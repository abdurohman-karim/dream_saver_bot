# rpc.py
import httpx
import logging
from config import RPC_URL, RPC_TOKEN


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
