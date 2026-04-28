from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from database import db
from states import AdminReplyStates
from config import ADMIN_ID
import asyncio
import logging

logger = logging.getLogger(__name__)


async def start_broadcast(message: types.Message):
    """Start broadcast process (admin only)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ غير مصرح لك بهذا الأمر", parse_mode='Markdown')
        return

    await message.answer("📢 **أرسل رسالة الإذاعة:**\n\n📝 سيتم إرسالها لجميع المستخدمين", parse_mode='Markdown')
    await AdminReplyStates.WAITING_BROADCAST.set()


async def send_broadcast(message: types.Message, state: FSMContext):
    """Send broadcast message to all users (admin only)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ غير مصرح لك بهذا الأمر")
        await state.finish()
        return

    broadcast_text = message.text

    if not broadcast_text:
        await message.answer("⚠️ **الرجاء إرسال نص الإذاعة**", parse_mode='Markdown')
        await state.finish()
        return

    # Confirmation prompt
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_broadcast"),
        types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_broadcast")
    )

    await message.answer(
        f"📢 **تأكيد الإذاعة**\n\n"
        f"📝 **الرسالة:**\n{broadcast_text}\n\n"
        f"⚠️ سيتم إرسالها لجميع المستخدمين.\n"
        f"هل أنت متأكد؟",
        reply_markup=markup,
        parse_mode='Markdown'
    )

    # Store broadcast message in state
    await state.update_data(broadcast_message=broadcast_text)


async def confirm_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    """Confirm and send broadcast"""
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    data = await state.get_data()
    broadcast_text = data.get('broadcast_message')

    if not broadcast_text:
        await callback_query.message.edit_text("❌ **لم يتم العثور على رسالة الإذاعة**", parse_mode='Markdown')
        await state.finish()
        return

    # Get all users
    users = db.get_all_users()
    count = 0
    failed = 0

    # Send broadcast message
    for user in users:
        try:
            await callback_query.bot.send_message(
                user[0],
                f"📢 **إذاعة عامة**\n\n{broadcast_text}",
                parse_mode='Markdown'
            )
            count += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to send broadcast to {user[0]}: {e}")

    # Log admin action
    db.log_admin_action(ADMIN_ID, 'broadcast', None, None, f'sent to {count} users, failed: {failed}')

    # Send result to admin
    result_text = f"✅ **تم إرسال الإذاعة بنجاح**\n\n"
    result_text += f"📨 **تم الإرسال لـ:** {count} مستخدم\n"
    if failed > 0:
        result_text += f"❌ **فشل الإرسال لـ:** {failed} مستخدم"

    await callback_query.message.edit_text(result_text, parse_mode='Markdown')
    await state.finish()
    await callback_query.answer()


async def cancel_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    await callback_query.message.edit_text("❌ **تم إلغاء الإذاعة**", parse_mode='Markdown')
    await state.finish()
    await callback_query.answer()


def register_broadcast_handlers(dp: Dispatcher):
    """Register broadcast handlers"""
    dp.register_message_handler(start_broadcast, lambda m: m.text == '📢 إذاعة' and m.from_user.id == ADMIN_ID, state='*')
    dp.register_message_handler(send_broadcast, state=AdminReplyStates.WAITING_BROADCAST)
    dp.register_callback_query_handler(confirm_broadcast, lambda c: c.data == 'confirm_broadcast', state='*')
    dp.register_callback_query_handler(cancel_broadcast, lambda c: c.data == 'cancel_broadcast', state='*')