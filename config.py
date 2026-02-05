import os

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:5136/api").rstrip("/")

RPC_URL = f"{BACKEND_BASE_URL}/rpc"
RPC_TOKEN = os.getenv("RPC_TOKEN", "your_secret_token")

TELEGRAM_REGISTER_URL = f"{BACKEND_BASE_URL}/telegram/register"
TELEGRAM_STATUS_URL = f"{BACKEND_BASE_URL}/telegram/status"

BOT_TOKEN = "8308593226:AAH4leywDJwk2s_m9uiDBfMJdqyxseaOmxM"
