from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from database import db
from states import AdminReplyStates
from config import ADMIN_ID, TIMEZONE
from datetime import datetime

async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ========== Ban User - Direct Command ==========
async def ban_user_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "⚠️ **طريقة الاستخدام:**\n"
            "/ban_user <معرف_المستخدم> [السبب]\n\n"
            "مثال:\n"
            "/ban_user 123456789\n"
            "/ban_user @username سبب الحظر",
            parse_mode='Markdown'
        )
        return

    target = parts[1]
    reason = parts[2] if len(parts) > 2 else "بدون سبب"

    user_id = None
    user_name = None
    username = None

    if target.startswith('@'):
        username = target[1:]
        db.cursor.execute('SELECT user_id, full_name FROM users WHERE username = ?', (username,))
        row = db.cursor.fetchone()
        if row:
            user_id = row[0]
            user_name = row[1]
        else:
            await message.answer(f"❌ المستخدم {target} غير موجود")
            return
    else:
        try:
            user_id = int(target)
            db.cursor.execute('SELECT full_name, username FROM users WHERE user_id = ?', (user_id,))
            row = db.cursor.fetchone()
            if row:
                user_name = row[0]
                username = row[1]
            else:
                await message.answer(f"❌ المستخدم {user_id} غير موجود")
                return
        except ValueError:
            await message.answer("❌ معرف المستخدم يجب أن يكون رقماً أو يبدأ بـ @")
            return

    db.ban_user(user_id)
    db.log_admin_action(ADMIN_ID, 'ban', user_id, None, reason)

    ban_message = f"🚫 **تم حظرك من البوت**\n\n📝 **السبب:** {reason}"
    await message.bot.send_message(user_id, ban_message, parse_mode='Markdown')

    await message.answer(
        f"✅ **تم حظر المستخدم بنجاح**\n\n"
        f"👤 {user_name}\n"
        f"🆔 {user_id}\n"
        f"📝 @{username if username else 'لا يوجد'}\n"
        f"📋 **السبب:** {reason}",
        parse_mode='Markdown'
    )

# ========== Unban User - Direct Command ==========
async def unban_user_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ استخدم: /unban_user 123456789", parse_mode='Markdown')
        return

    target = parts[1]
    user_id = None
    user_name = None
    username = None

    if target.startswith('@'):
        username = target[1:]
        db.cursor.execute('SELECT user_id, full_name FROM users WHERE username = ?', (username,))
        row = db.cursor.fetchone()
        if row:
            user_id = row[0]
            user_name = row[1]
        else:
            await message.answer(f"❌ المستخدم {target} غير موجود")
            return
    else:
        try:
            user_id = int(target)
            db.cursor.execute('SELECT full_name, username FROM users WHERE user_id = ?', (user_id,))
            row = db.cursor.fetchone()
            if row:
                user_name = row[0]
                username = row[1]
            else:
                await message.answer(f"❌ المستخدم {user_id} غير موجود")
                return
        except ValueError:
            await message.answer("❌ معرف المستخدم يجب أن يكون رقماً")
            return

    if not db.is_user_banned(user_id):
        await message.answer(f"ℹ️ المستخدم {user_name} ليس محظوراً حالياً")
        return

    db.unban_user(user_id)
    db.log_admin_action(ADMIN_ID, 'unban', user_id, None, None)

    await message.bot.send_message(user_id, "✅ تم فك حظرك، يمكنك استخدام البوت مرة أخرى")

    await message.answer(
        f"✅ **تم فك حظر المستخدم بنجاح**\n\n"
        f"👤 {user_name}\n"
        f"🆔 {user_id}\n"
        f"📝 @{username if username else 'لا يوجد'}",
        parse_mode='Markdown'
    )

# ========== Banned Users List ==========
async def banned_list_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    db.cursor.execute('''
        SELECT user_id, full_name, username, details, date 
        FROM banned_users 
        JOIN users ON banned_users.user_id = users.user_id
        ORDER BY date DESC
    ''')
    banned = db.cursor.fetchall()

    if not banned:
        await message.answer("📭 لا يوجد مستخدمين محظورين حالياً", parse_mode='Markdown')
        return

    text = "🚫 **قائمة المحظورين**\n\n"
    for b in banned[:20]:
        text += f"👤 {b[1]}\n🆔 `{b[0]}`\n📝 @{b[2] if b[2] else 'لا يوجد'}\n📋 {b[3] if b[3] else 'بدون سبب'}\n📅 {b[4][:16]}\n─" * 20 + "\n"

    if len(banned) > 20:
        text += f"\n... و {len(banned) - 20} آخرين"

    await message.answer(text, parse_mode='Markdown')

# ========== Ban via Admin Panel (with reason) ==========
async def ban_with_reason(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    data = await state.get_data()
    user_id = data.get('ban_user')

    if not user_id:
        await message.answer("❌ لم يتم تحديد المستخدم")
        await state.finish()
        return

    reason = message.text
    user_info = db.get_user_info(user_id)

    db.ban_user(user_id)
    db.log_admin_action(ADMIN_ID, 'ban', user_id, None, reason)

    await message.bot.send_message(user_id, f"🚫 **تم حظرك من البوت**\n\n📝 **السبب:** {reason}", parse_mode='Markdown')

    await message.answer(
        f"✅ **تم حظر المستخدم بنجاح**\n\n"
        f"👤 {user_info['name'] if user_info else 'غير معروف'}\n"
        f"🆔 {user_id}\n"
        f"📝 @{user_info['username'] if user_info else 'لا يوجد'}\n"
        f"📋 **السبب:** {reason}"
    )

    await state.finish()

def register_ban_handlers(dp: Dispatcher):
    dp.register_message_handler(ban_user_command, lambda m: m.text and m.text.startswith('/ban_user'), state='*')
    dp.register_message_handler(unban_user_command, lambda m: m.text and m.text.startswith('/unban_user'), state='*')
    dp.register_message_handler(banned_list_command, lambda m: m.text and m.text.startswith('/banned_list'), state='*')
    dp.register_message_handler(ban_with_reason, state=AdminReplyStates.WAITING_BAN_REASON)