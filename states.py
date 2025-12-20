from aiogram.fsm.state import State, StatesGroup

class Booking(StatesGroup):
    pc = State()
    date = State()
    time_from = State()
    time_to = State()

class Support(StatesGroup):
    message = State()
