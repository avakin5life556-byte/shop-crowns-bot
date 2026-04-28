from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from database import db
from keyboards import get_main_keyboard
from config import ADMIN_ID, TIMEZONE
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username or 'No username'

    # Register user in database
    db.register_user(user_id, full_name, username)
    lang = db.get_user_language(user_id)

    # Clear any active state
    await state.finish()

    # Send welcome message
    welcome_text = "اهلاً بك في متجر Shop Crowns 🎉🎁\nاختر من القائمة 👇" if lang == 'ar' else "Welcome to Shop Crowns 🎉🎁\nChoose from the menu 👇"

    await message.answer(welcome_text, reply_markup=get_main_keyboard(lang))

    # Notify admin about new user
    now = datetime.now(TIMEZONE)
    admin_msg = f"🆕 مستخدم جديد دخل البوت\n👤 {full_name}\n🆔 {user_id}\n📝 @{username}\n📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    await message.bot.send_message(ADMIN_ID, admin_msg)

    logger.info(f"New user registered: {user_id} - {full_name}")


def register_start_handlers(dp: Dispatcher):
    """Register start command handlers"""
    dp.register_message_handler(cmd_start, commands=['start'], state='*')
