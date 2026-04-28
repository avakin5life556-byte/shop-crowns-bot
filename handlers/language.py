from aiogram import types
from aiogram.dispatcher import Dispatcher
from database import db
from keyboards import get_main_keyboard
import logging

logger = logging.getLogger(__name__)


async def change_language(message: types.Message):
    """Display language selection menu"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )

    await message.answer(
        "🌍 اختر لغتك:" if lang == 'ar' else "🌍 Choose your language:",
        reply_markup=markup
    )


async def set_language(callback_query: types.CallbackQuery):
    """Set user's language preference"""
    user_id = callback_query.from_user.id
    new_lang = callback_query.data.split('_')[1]

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if new_lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    # Update language in database
    db.set_user_language(user_id, new_lang)

    # Confirm language change
    await callback_query.message.edit_text(
        "✅ تم تغيير اللغة بنجاح" if new_lang == 'ar' else "✅ Language changed successfully",
        reply_markup=None
    )

    # Send welcome message in new language
    welcome_text = "اهلاً بك في متجر Shop Crowns 🎉🎁\nاختر من القائمة 👇" if new_lang == 'ar' else "Welcome to Shop Crowns 🎉🎁\nChoose from the menu 👇"

    await callback_query.message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(new_lang)
    )

    logger.info(f"User {user_id} changed language to {new_lang}")
    await callback_query.answer()


def register_language_handlers(dp: Dispatcher):
    """Register language handlers"""
    dp.register_message_handler(change_language, lambda m: m.text in ['🌍 تغيير اللغة', '🌍 Change Language'], state='*')
    dp.register_callback_query_handler(set_language, lambda c: c.data and c.data.startswith('lang_'), state='*')