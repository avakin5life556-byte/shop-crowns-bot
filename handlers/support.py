from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import db
from keyboards import get_main_keyboard, get_live_chat_keyboard, get_support_rating_keyboard
from states import ComplaintStates, LiveChatStates, AdminReplyStates
from config import ADMIN_ID, TIMEZONE
from datetime import datetime
from utils.helpers import is_rate_limited
import logging

logger = logging.getLogger(__name__)


# ========== Complaint System ==========
async def show_complaint(message: types.Message, state: FSMContext):
    """Show complaint entry point"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    await message.answer(
        "📝 اكتب شكواك أو استفسارك:" if lang == 'ar' else "📝 Write your complaint or inquiry:"
    )
    await ComplaintStates.WAITING_MESSAGE.set()


async def receive_complaint(message: types.Message, state: FSMContext):
    """Receive and process complaint"""
    user_id = message.from_user.id
    complaint_text = message.text
    lang = db.get_user_language(user_id)

    # Rate limiting
    if is_rate_limited(user_id, 'complaint', limit=3, window=300):
        await message.answer(
            "⚠️ أرسلت شكاوى كثيرة، انتظر قليلاً" if lang == 'ar' else "⚠️ Too many complaints, please wait",
            reply_markup=get_main_keyboard(lang)
        )
        await state.finish()
        return

    # Create ticket
    ticket_number, ticket_id = db.create_ticket(user_id, 'complaint', complaint_text)
    user_info = db.get_user_info(user_id)
    now = datetime.now(TIMEZONE)

    await message.answer(
        "✅ تم إرسال شكواك، سيتم الرد عليك قريباً" if lang == 'ar' else "✅ Your complaint has been sent, you will be replied soon",
        reply_markup=get_main_keyboard(lang)
    )

    # Notify admin
    admin_msg = f"📝 **شكوى جديدة**\n"
    admin_msg += f"🎫 **رقم التذكرة:** {ticket_number}\n"
    admin_msg += f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}\n"
    admin_msg += f"🆔 **المعرف:** {user_id}\n"
    admin_msg += f"📝 **اليوزر:** @{user_info['username'] if user_info else 'لا يوجد'}\n"
    admin_msg += f"🗣️ **اللغة:** {lang}\n"
    admin_msg += f"💬 **الرسالة:** {complaint_text}\n"
    admin_msg += f"📅 **التاريخ:** {now.strftime('%Y-%m-%d %H:%M:%S')}"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 رد", callback_data=f"reply_ticket_{ticket_number}"),
        types.InlineKeyboardButton("🔓 فتح محادثة", callback_data=f"open_chat_{ticket_number}"),
        types.InlineKeyboardButton("✅ إغلاق التذكرة", callback_data=f"close_ticket_{ticket_number}")
    )

    await message.bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode='Markdown')
    await state.finish()


# ========== Contact Us / Live Chat ==========
async def contact_us(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle contact us button - open live chat"""
    user_id = callback_query.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    # Rate limiting
    if is_rate_limited(user_id, 'chat', limit=5, window=120):
        await callback_query.answer("⚠️ أرسلت طلبات كثيرة، انتظر قليلاً" if lang == 'ar' else "⚠️ Too many requests, wait", show_alert=True)
        return

    # Check existing chat
    existing = db.get_active_chat(user_id)
    if existing:
        await callback_query.answer("⚠️ محادثة مفتوحة بالفعل" if lang == 'ar' else "⚠️ Chat already open", show_alert=True)
        return

    # Create ticket and chat session
    ticket_number, ticket_id = db.create_ticket(user_id, 'live_chat', 'فتح محادثة دعم مباشر')
    session_id = db.create_chat_session(user_id, None, ticket_id)

    await state.update_data(chat_ticket=ticket_id, chat_session=session_id, in_chat=True)

    await callback_query.message.edit_text(
        "🔓 **تم فتح محادثة مع الدعم الفني**\nيمكنك كتابة رسالتك الآن" if lang == 'ar' else "🔓 **Live chat opened**\nYou can now send your message",
        reply_markup=get_live_chat_keyboard(),
        parse_mode='Markdown'
    )
    await callback_query.answer()


async def live_chat_message(message: types.Message, state: FSMContext):
    """Handle user messages in live chat"""
    user_id = message.from_user.id
    data = await state.get_data()

    if not data.get('in_chat'):
        return

    ticket_id = data.get('chat_ticket')
    if not ticket_id:
        return

    # Rate limiting
    if is_rate_limited(user_id, 'chat_message', limit=10, window=30):
        await message.answer("⚠️ أرسلت رسائل كثيرة، انتظر قليلاً")
        return

    # Save message to database
    db.add_ticket_message(ticket_id, user_id, message.text)

    # Forward to admin
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("💬 رد", callback_data=f"reply_user_{user_id}"),
        types.InlineKeyboardButton("🔒 إنهاء المحادثة", callback_data=f"end_chat_{user_id}")
    )

    await message.bot.send_message(
        ADMIN_ID,
        f"💬 **رسالة من المستخدم {user_id}**\n\n{message.text}",
        reply_markup=admin_markup,
        parse_mode='Markdown'
    )

    await message.answer("✅ تم إرسال رسالتك")


async def admin_reply_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Start admin reply process"""
    user_id = int(callback_query.data.split('_')[2])

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    await state.update_data(reply_to_user=user_id)
    await callback_query.message.answer("💬 اكتب ردك للمستخدم:")
    await AdminReplyStates.WAITING_REPLY.set()
    await callback_query.answer()


async def admin_send_reply(message: types.Message, state: FSMContext):
    """Send reply from admin to user"""
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    user_id = data.get('reply_to_user')

    if not user_id:
        await message.answer("❌ لم يتم تحديد المستخدم")
        await state.finish()
        return

    reply_text = message.text

    # Find active chat
    active_chat = db.get_active_chat(user_id)
    if active_chat:
        ticket_id = active_chat[3]
        db.add_ticket_message(ticket_id, ADMIN_ID, reply_text)

    # Send reply to user
    await message.bot.send_message(
        user_id,
        f"📨 **رد من الدعم:**\n{reply_text}",
        reply_markup=get_live_chat_keyboard(),
        parse_mode='Markdown'
    )

    await message.answer(f"✅ تم إرسال الرد للمستخدم {user_id}")
    await state.finish()


async def end_chat(callback_query: types.CallbackQuery, state: FSMContext):
    """End live chat session"""
    user_id = callback_query.from_user.id
    lang = db.get_user_language(user_id)

    # Close chat session in database
    chat_session = db.get_active_chat(user_id)
    if chat_session:
        db.close_chat_session(chat_session[0])

    # Close ticket
    data = await state.get_data()
    ticket_id = data.get('chat_ticket')
    if ticket_id:
        from database import db as db_instance
        db_instance.cursor.execute('SELECT ticket_number FROM tickets WHERE id = ?', (ticket_id,))
        row = db_instance.cursor.fetchone()
        if row:
            db.close_ticket(row[0])

    await state.update_data(in_chat=False, chat_ticket=None, chat_session=None)

    await callback_query.message.edit_text(
        "🔒 **تم إنهاء المحادثة**\nشكراً لتواصلك معنا" if lang == 'ar' else "🔒 **Chat ended**\nThank you for contacting us",
        reply_markup=get_support_rating_keyboard(),
        parse_mode='Markdown'
    )
    await callback_query.answer()


async def support_rating(callback_query: types.CallbackQuery):
    """Handle support rating"""
    user_id = callback_query.from_user.id
    rating = int(callback_query.data.split('_')[-1])
    lang = db.get_user_language(user_id)

    db.save_rating(user_id, rating, 'support', '')

    await callback_query.message.edit_text(
        "🙏 **شكراً لتقييمك لخدمة الدعم**" if lang == 'ar' else "🙏 **Thank you for rating our support**",
        reply_markup=get_main_keyboard(lang),
        parse_mode='Markdown'
    )
    await callback_query.answer()


async def admin_reply_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    """Reply to a ticket as admin"""
    ticket_number = callback_query.data.split('_')[2]

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    await state.update_data(reply_ticket=ticket_number)
    await callback_query.message.answer("💬 اكتب ردك على هذه التذكرة:")
    await AdminReplyStates.WAITING_REPLY.set()
    await callback_query.answer()


async def send_ticket_reply(message: types.Message, state: FSMContext):
    """Send ticket reply to user"""
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    ticket_number = data.get('reply_ticket')

    if not ticket_number:
        await message.answer("❌ لم يتم تحديد التذكرة")
        await state.finish()
        return

    from database import db as db_instance
    db_instance.cursor.execute('SELECT id, user_id FROM tickets WHERE ticket_number = ?', (ticket_number,))
    ticket = db_instance.cursor.fetchone()

    if not ticket:
        await message.answer("❌ التذكرة غير موجودة")
        await state.finish()
        return

    ticket_id, user_id = ticket

    db.add_ticket_message(ticket_id, ADMIN_ID, message.text)

    await message.bot.send_message(
        user_id,
        f"📨 **رد على تذكرتك #{ticket_number}:**\n{message.text}",
        parse_mode='Markdown'
    )

    await message.answer(f"✅ تم إرسال الرد على التذكرة {ticket_number}")
    await state.finish()


async def open_chat_from_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    """Open chat from ticket"""
    ticket_number = callback_query.data.split('_')[2]

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    from database import db as db_instance
    db_instance.cursor.execute('SELECT id, user_id FROM tickets WHERE ticket_number = ?', (ticket_number,))
    ticket = db_instance.cursor.fetchone()

    if not ticket:
        await callback_query.answer("التذكرة غير موجودة", show_alert=True)
        return

    ticket_id, user_id = ticket

    session_id = db.create_chat_session(user_id, ADMIN_ID, ticket_id)

    await state.update_data(chat_ticket=ticket_id, chat_session=session_id, in_chat=True)

    await callback_query.message.answer(f"💬 **تم فتح محادثة مع المستخدم {user_id}**\nأرسل رسالتك الآن", parse_mode='Markdown')
    await callback_query.bot.send_message(
        user_id,
        "🔓 **تم فتح محادثة مع الدعم الفني**\nيمكنك كتابة رسالتك الآن",
        reply_markup=get_live_chat_keyboard(),
        parse_mode='Markdown'
    )
    await callback_query.answer()


async def close_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    """Close a ticket"""
    ticket_number = callback_query.data.split('_')[2]

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    db.close_ticket(ticket_number)

    # Close any active chat
    from database import db as db_instance
    db_instance.cursor.execute('SELECT user_id FROM tickets WHERE ticket_number = ?', (ticket_number,))
    row = db_instance.cursor.fetchone()
    if row:
        chat = db.get_active_chat(row[0])
        if chat:
            db.close_chat_session(chat[0])

    await callback_query.message.edit_text(f"✅ **تم إغلاق التذكرة {ticket_number}**", parse_mode='Markdown')
    await callback_query.answer()


# ========== Register Handlers ==========
def register_support_handlers(dp: Dispatcher):
    """Register all support handlers"""
    # Complaint
    dp.register_message_handler(show_complaint, lambda m: m.text in ['📝 الشكاوى', '📝 Complaints'], state='*')
    dp.register_message_handler(receive_complaint, state=ComplaintStates.WAITING_MESSAGE)

    # Contact / Live Chat
    dp.register_callback_query_handler(contact_us, lambda c: c.data == 'contact_us', state='*')
    dp.register_message_handler(live_chat_message, state='*')

    # Admin reply to user
    dp.register_callback_query_handler(admin_reply_start, lambda c: c.data and c.data.startswith('reply_user_'), state='*')
    dp.register_message_handler(admin_send_reply, state=AdminReplyStates.WAITING_REPLY)

    # Admin ticket reply
    dp.register_callback_query_handler(admin_reply_ticket, lambda c: c.data and c.data.startswith('reply_ticket_'), state='*')
    dp.register_message_handler(send_ticket_reply, state=AdminReplyStates.WAITING_REPLY)

    # End chat
    dp.register_callback_query_handler(end_chat, lambda c: c.data == 'end_chat', state='*')

    # Open chat from ticket
    dp.register_callback_query_handler(open_chat_from_ticket, lambda c: c.data and c.data.startswith('open_chat_'), state='*')

    # Close ticket
    dp.register_callback_query_handler(close_ticket, lambda c: c.data and c.data.startswith('close_ticket_'), state='*')

    # Rating
    dp.register_callback_query_handler(support_rating, lambda c: c.data and c.data.startswith('support_rate_'), state='*')
