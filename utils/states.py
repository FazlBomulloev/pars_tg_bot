from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_source = State()
    waiting_for_source_delete = State()
    waiting_for_keyword = State()
    waiting_for_keyword_delete = State()
    waiting_for_delay = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()
    waiting_for_history_selection = State() 
