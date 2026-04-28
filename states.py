from aiogram.dispatcher.filters.state import State, StatesGroup


class AdminReplyStates(StatesGroup):
    WAITING_BROADCAST = State()


class ChangeNameStates(StatesGroup):
    waiting_for_name = State()


class ChangePhotoStates(StatesGroup):
    waiting_for_photo = State()