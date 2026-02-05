from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import main_menu


async def get_user_flags(tg_user_id: int) -> dict:
    flags = {
        "has_goals": True,
        "has_transactions": True,
        "has_budget": True,
        "smart_save_available": True,
        "is_new_user": False,
    }

    try:
        goals = await rpc("goal.list", {"tg_user_id": tg_user_id})
        flags["has_goals"] = bool(goals.get("goals", []))
    except (RPCError, RPCTransportError):
        return flags

    try:
        month_str = date.today().strftime("%Y-%m")
        budget = await rpc("budget.getMonth", {
            "tg_user_id": tg_user_id,
            "month": month_str,
        })
        flags["has_budget"] = bool(budget.get("exists", True))
    except (RPCError, RPCTransportError):
        flags["has_budget"] = True

    try:
        today = date.today().isoformat()
        daily = await rpc("transaction.getDaily", {
            "tg_user_id": tg_user_id,
            "date": today,
        })
        flags["has_transactions"] = bool(daily.get("items", []))
    except (RPCError, RPCTransportError):
        flags["has_transactions"] = True

    flags["smart_save_available"] = flags["has_goals"] and flags["has_budget"]
    flags["is_new_user"] = not flags["has_goals"] and not flags["has_budget"] and not flags["has_transactions"]
    return flags


async def get_main_menu(tg_user_id: int):
    flags = await get_user_flags(tg_user_id)
    return main_menu(flags)
