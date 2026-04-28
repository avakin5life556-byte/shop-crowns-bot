from aiogram import types
from aiogram.dispatcher import Dispatcher
from database import db
from keyboards import get_rating_keyboard, get_main_keyboard
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)


async def show_rating(message: types.Message):
    """Display rating menu"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    await message.answer(
        "⭐ قيم تجربتك مع البوت:" if lang == 'ar' else "⭐ Rate your experience with the bot:",
        reply_markup=get_rating_keyboard()
    )


async def rating_callback(callback_query: types.CallbackQuery):
    """Handle rating selection"""
    user_id = callback_query.from_user.id
    rating = int(callback_query.data.split('_')[1])
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    # Save rating to database
    db.save_rating(user_id, rating, 'bot', '')

    # Send thank you message
    await callback_query.message.edit_text(
        "🙏 شكراً لتقييمك!" if lang == 'ar' else "🙏 Thank you for rating!",
        reply_markup=get_main_keyboard(lang)
    )

    # Notify admin
    user_info = db.get_user_info(user_id)
    admin_msg = f"⭐ **تقييم جديد**\n\n"
    admin_msg += f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}\n"
    admin_msg += f"🆔 **المعرف:** {user_id}\n"
    admin_msg += f"⭐ **التقييم:** {rating}/5"

    await callback_query.bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')

    logger.info(f"User {user_id} rated bot: {rating}/5")
    await callback_query.answer()


def register_rating_handlers(dp: Dispatcher):
    """Register rating handlers"""
    dp.register_message_handler(show_rating, lambda m: m.text in ['⭐ تقييم البوت', '⭐ Rate Bot'], state='*')
    dp.register_callback_query_handler(rating_callback, lambda c: c.data and c.data.startswith('rate_'), state='*')