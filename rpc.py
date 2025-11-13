import httpx
from config import RPC_URL, RPC_TOKEN


async def rpc(method: str, params: dict = None):
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or {},
            },
            headers={
                "Authorization": f"Bearer {RPC_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        return resp.json()