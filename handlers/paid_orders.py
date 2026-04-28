from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import db
from keyboards import get_order_admin_keyboard, get_contact_button, get_main_keyboard
from config import ADMIN_ID, TIMEZONE
from datetime import datetime
from utils.timeout_manager import timeout_manager
from utils.helpers import safe_json_dumps, is_rate_limited
import json

# Paid order types with bilingual support
PAID_ORDER_TYPES = {
    'buy_crowns': {'ar': '🟣 شراء كراونز', 'en': '🟣 Buy Crowns'},
    'buy_coins': {'ar': '🟡 شراء كوينز', 'en': '🟡 Buy Coins'},
    'buy_vip': {'ar': '💳 شراء عضويات', 'en': '💳 Buy VIP'},
    'boost_account': {'ar': '🤖 تعزيز الحسابات', 'en': '🤖 Boost Account'},
    'buy_likes': {'ar': '🚀 لايكات ومشاهدات', 'en': '🚀 Likes & Views'},
    'other_games': {'ar': '🎮 ألعاب أخرى', 'en': '🎮 Other Games'}
}

async def show_paid_orders(message: types.Message):
    """Display paid orders menu"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    
    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for key, texts in PAID_ORDER_TYPES.items():
        display = texts['ar'] if lang == 'ar' else texts['en']
        buttons.append(types.InlineKeyboardButton(display, callback_data=key))

    # Add buttons in rows of 2
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.row(buttons[i])

    markup.add(types.InlineKeyboardButton("🔙 رجوع" if lang == 'ar' else "🔙 Back", callback_data="back_main"))

    await message.answer(
        "💰 طلبات الشراء" if lang == 'ar' else "💰 Purchase Requests",
        reply_markup=markup
    )

async def paid_order_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle paid order selection"""
    user_id = callback_query.from_user.id
    order_type = callback_query.data
    lang = db.get_user_language(user_id)
    order_name = PAID_ORDER_TYPES.get(order_type, {'ar': order_type, 'en': order_type})
    order_display = order_name['ar'] if lang == 'ar' else order_name['en']
    
    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return
    
    # Rate limiting
    if is_rate_limited(user_id, 'paid_order', limit=5, window=60):
        await callback_query.answer(
            "⚠️ أرسلت طلبات كثيرة، انتظر قليلاً" if lang == 'ar' else "⚠️ Too many requests, please wait",
            show_alert=True
        )
        return

    # Create order
    order_data_dict = {'type': order_type, 'display': order_display}
    order_data = safe_json_dumps(order_data_dict)
    order_number = db.create_order(user_id, order_display, order_data)
    
    # Set timeout
    await timeout_manager.set_timeout(order_number, user_id, callback_query.bot)

    await callback_query.message.edit_text(
        "✅ تم استلام طلبك\nسيتم التواصل معك قريباً" if lang == 'ar' else "✅ Request received\nWe will contact you soon",
        reply_markup=None
    )

    # Send contact button
    await callback_query.message.answer(
        "💬 تواصل مع الدعم" if lang == 'ar' else "💬 Contact Support",
        reply_markup=get_contact_button(lang)
    )

    # Prepare admin message
    user_info = db.get_user_info(user_id)
    now = datetime.now(TIMEZONE)
    remaining = await timeout_manager.get_remaining_time(order_number)

    admin_msg_lines = [
        f"📋 **طلب شراء جديد**",
        f"📌 **رقم:** {order_number}",
        f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}",
        f"🆔 **المعرف:** {user_id}",
        f"📝 **اليوزر:** @{user_info['username'] if user_info else 'لا يوجد'}",
        f"🗣️ **اللغة:** {db.get_user_language(user_id)}",
        f"🌍 **البلد:** {user_info['country'] if user_info else 'غير معروف'}",
        f"📦 **النوع:** {order_display}",
        f"📅 **التاريخ:** {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"⏰ **المدة المتبقية:** {remaining} دقيقة"
    ]
    admin_msg = "\n".join(admin_msg_lines)

    await callback_query.bot.send_message(
        ADMIN_ID,
        admin_msg,
        reply_markup=get_order_admin_keyboard(order_number, user_id),
        parse_mode='Markdown'
    )

    await callback_query.answer()

def register_paid_orders_handlers(dp: Dispatcher):
    """Register all paid orders handlers"""
    dp.register_message_handler(show_paid_orders, lambda m: m.text in ['💰 طلبات الشراء', '💰 Purchase Requests'], state='*')
    dp.register_callback_query_handler(paid_order_callback, lambda c: c.data in PAID_ORDER_TYPES.keys(), state='*')