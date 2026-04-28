from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import db
from keyboards import get_admin_keyboard, get_order_admin_keyboard, get_live_chat_keyboard
from states import AdminReplyStates
from config import ADMIN_ID, TIMEZONE
from datetime import datetime
from utils.timeout_manager import timeout_manager

async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def show_admin_panel(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer("👑 **لوحة التحكم - الأدمن**", reply_markup=get_admin_keyboard(), parse_mode='Markdown')

async def show_stats(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    stats = db.get_stats()
    text = f"📊 **إحصائيات البوت**\n\n"
    text += f"👥 المستخدمين النشطين: {stats['active']}\n"
    text += f"🚫 المحظورين: {stats['banned']}\n"
    text += f"📦 إجمالي الطلبات: {stats['total_orders']}\n"
    text += f"⏳ طلبات معلقة: {stats['pending_orders']}"
    await message.answer(text, parse_mode='Markdown')

async def show_orders(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    orders = db.get_pending_orders()
    if not orders:
        await message.answer("📭 لا توجد طلبات معلقة", parse_mode='Markdown')
        return

    for order in orders[:10]:
        user_info = db.get_user_info(order[2])
        order_data = order[4] if order[4] else '{}'

        text = f"📋 **الطلب #{order[1]}**\n"
        text += f"👤 **الاسم:** {user_info['name'] if user_info else 'غير معروف'}\n"
        text += f"🆔 **المعرف:** {order[2]}\n"
        text += f"📝 **اليوزر:** @{user_info['username'] if user_info else 'لا يوجد'}\n"
        text += f"🗣️ **اللغة:** {user_info['lang'] if user_info else 'ar'}\n"
        text += f"🌍 **البلد:** {user_info['country'] if user_info else 'غير معروف'}\n"
        text += f"📦 **النوع:** {order[3]}\n"
        text += f"📅 **التاريخ:** {order[6][:16]}\n"
        text += f"📊 **البيانات:** {order_data[:100]}"

        remaining = await timeout_manager.get_remaining_time(order[1])
        if remaining > 0:
            text += f"\n⏰ **المدة المتبقية:** {remaining} دقيقة"

        await message.answer(text, reply_markup=get_order_admin_keyboard(order[1], order[2]), parse_mode='Markdown')

async def admin_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if not await is_admin(user_id):
        await callback_query.answer("⛔ غير مصرح", show_alert=True)
        return

    data = callback_query.data

    # Handle done (تم التنفيذ)
    if data.startswith('done_'):
        _, order_number, target_user = data.split('_')
        target_user = int(target_user)
        
        # Cancel timeout for this order
        await timeout_manager.cancel_timeout(order_number)
        
        # Update order status
        db.update_order_status(order_number, 'completed')
        db.log_admin_action(user_id, 'order_completed', target_user, order_number, None)

        await callback_query.bot.send_message(
            target_user,
            "✅ **تم تنفيذ طلبك بنجاح**\nيمكنك مراجعة حسابك الآن",
            parse_mode='Markdown'
        )
        await callback_query.message.edit_text(f"✅ **تم تنفيذ الطلب #{order_number}**")
        await callback_query.answer()

    # Handle exec (جاري التنفيذ)
    elif data.startswith('exec_'):
        _, order_number, target_user = data.split('_')
        target_user = int(target_user)
        
        # Refresh timeout (add extra 10 minutes)
        await timeout_manager.refresh_timeout(order_number, target_user, callback_query.bot, extra_minutes=10)
        
        # Update order status
        db.update_order_status(order_number, 'processing')
        db.log_admin_action(user_id, 'order_processing', target_user, order_number, None)

        await callback_query.bot.send_message(
            target_user,
            "🔄 **جاري تنفيذ طلبك**",
            parse_mode='Markdown'
        )
        await callback_query.message.edit_text(f"🔄 **تم بدء تنفيذ الطلب #{order_number}**")
        await callback_query.answer()

    # Handle cancel (إلغاء)
    elif data.startswith('cancel_'):
        _, order_number, target_user = data.split('_')
        target_user = int(target_user)
        
        # Cancel timeout
        await timeout_manager.cancel_timeout(order_number)
        
        # Update order status
        db.update_order_status(order_number, 'cancelled')
        db.log_admin_action(user_id, 'order_cancelled', target_user, order_number, None)

        await callback_query.bot.send_message(
            target_user,
            "❌ **تم إلغاء طلبك بسبب ضغط الطلبات**",
            parse_mode='Markdown'
        )
        await callback_query.message.edit_text(f"❌ **تم إلغاء الطلب #{order_number}**")
        await callback_query.answer()

    # Handle chat (تواصل)
    elif data.startswith('chat_'):
        _, order_number, target_user = data.split('_')
        target_user = int(target_user)

        # Cancel timeout? Optional - chat might still need timeout
        # await timeout_manager.cancel_timeout(order_number)

        ticket_number, ticket_id = db.create_ticket(target_user, 'order_chat', f'محادثة حول الطلب {order_number}')
        session_id = db.create_chat_session(target_user, user_id, ticket_id)

        await state.update_data(chat_user=target_user, chat_ticket=ticket_id, chat_session=session_id, in_chat=True)

        await callback_query.message.answer(f"💬 **تم فتح محادثة مع المستخدم {target_user}**\nأرسل رسالتك الآن", parse_mode='Markdown')
        await callback_query.bot.send_message(
            target_user,
            "🔓 **تم فتح محادثة مع الدعم الفني**\nيمكنك كتابة رسالتك الآن",
            reply_markup=get_live_chat_keyboard(),
            parse_mode='Markdown'
        )
        await callback_query.answer()

    # Handle ban (حظر)
    elif data.startswith('ban_'):
        _, order_number, target_user = data.split('_')
        target_user = int(target_user)

        await state.update_data(ban_user=target_user)
        await callback_query.message.answer("📝 **اكتب سبب الحظر:**", parse_mode='Markdown')
        await AdminReplyStates.WAITING_BAN_REASON.set()
        await callback_query.answer()

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(show_admin_panel, lambda m: m.text == '👑 لوحة التحكم' and m.from_user.id == ADMIN_ID)
    dp.register_message_handler(show_stats, lambda m: m.text == '📊 الإحصائيات' and m.from_user.id == ADMIN_ID)
    dp.register_message_handler(show_orders, lambda m: m.text == '📋 الطلبات' and m.from_user.id == ADMIN_ID)
    dp.register_callback_query_handler(admin_callback_handler, lambda c: c.data.startswith(('done_', 'exec_', 'cancel_', 'chat_', 'ban_')), state='*')