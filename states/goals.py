# states/goals.py
from aiogram.fsm.state import State, StatesGroup

class GoalStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_amount = State()
    waiting_for_icon = State()
    waiting_for_deadline = State()

class DepositGoal(StatesGroup):
    waiting_for_amount = State()
