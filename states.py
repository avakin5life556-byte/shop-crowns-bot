from aiogram.dispatcher.filters.state import State, StatesGroup

# ========== Free Orders States ==========
class ChangeNameStates(StatesGroup):
    CHECK_BALANCE = State()
    WAITING_NAME = State()
    WAITING_EMAIL = State()
    WAITING_PASSWORD = State()


class ChangePhotoStates(StatesGroup):
    CHECK_BALANCE = State()
    WAITING_PHOTO = State()
    WAITING_EMAIL = State()
    WAITING_PASSWORD = State()


# ========== Support States ==========
class ComplaintStates(StatesGroup):
    WAITING_MESSAGE = State()


class LiveChatStates(StatesGroup):
    ACTIVE = State()


# ========== Admin Reply States ==========
class AdminReplyStates(StatesGroup):
    WAITING_REPLY = State()
    WAITING_BAN_REASON = State()
    WAITING_BROADCAST = State()
