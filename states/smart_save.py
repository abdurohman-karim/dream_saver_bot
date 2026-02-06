# states/smart_save.py
from aiogram.fsm.state import State, StatesGroup


class SmartSaveFallback(StatesGroup):
    waiting_for_confirm = State()
