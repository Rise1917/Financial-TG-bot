from aiogram.fsm.state import State, StatesGroup


class ExpenseStates(StatesGroup):
    waiting_for_amount = State()


class StatementStates(StatesGroup):
    waiting_for_file = State()
