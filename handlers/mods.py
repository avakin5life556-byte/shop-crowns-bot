from aiogram import types
from aiogram.dispatcher import Dispatcher
from database import db
from config import MOD_LINKS
import logging

logger = logging.getLogger(__name__)

# Mods definitions with bilingual support
MODS = {
    'sky': {'ar': '☁️ مود سكاي', 'en': '☁️ Sky Mod', 'icon': '☁️'},
    'bull': {'ar': '🐂 مود الثور', 'en': '🐂 Bull Mod', 'icon': '🐂'},
    'gold': {'ar': '👑 مود جولد', 'en': '👑 Gold Mod', 'icon': '👑'}
}


async def show_mods(message: types.Message):
    """Display mods menu"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    for key, texts in MODS.items():
        display = texts['ar'] if lang == 'ar' else texts['en']
        markup.add(types.InlineKeyboardButton(display, callback_data=f"mod_{key}"))

    markup.add(types.InlineKeyboardButton("🔙 رجوع" if lang == 'ar' else "🔙 Back", callback_data="back_main"))

    await message.answer(
        "🎮 المودات" if lang == 'ar' else "🎮 Mods",
        reply_markup=markup
    )


async def mod_callback(callback_query: types.CallbackQuery):
    """Handle mod selection and send link"""
    user_id = callback_query.from_user.id
    mod_key = callback_query.data.split('_')[1]
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    # Get appropriate link based on mod
    if mod_key == 'sky':
        link = MOD_LINKS['sky']
        mod_name = MODS['sky']['ar'] if lang == 'ar' else MODS['sky']['en']
    elif mod_key == 'bull':
        link = f"{MOD_LINKS['bull']}\n{MOD_LINKS['bull_alt']}"
        mod_name = MODS['bull']['ar'] if lang == 'ar' else MODS['bull']['en']
    else:  # gold
        link = MOD_LINKS['gold']
        mod_name = MODS['gold']['ar'] if lang == 'ar' else MODS['gold']['en']

    message_text = f"📥 **{mod_name}**\n\n🔗 **الرابط:**\n{link}" if lang == 'ar' else f"📥 **{mod_name}**\n\n🔗 **Link:**\n{link}"

    await callback_query.message.answer(message_text, parse_mode='Markdown')
    await callback_query.answer()


def register_mods_handlers(dp: Dispatcher):
    """Register mods handlers"""
    dp.register_message_handler(show_mods, lambda m: m.text in ['🎮 المودات', '🎮 Mods'], state='*')
    dp.register_callback_query_handler(mod_callback, lambda c: c.data and c.data.startswith('mod_'), state='*')