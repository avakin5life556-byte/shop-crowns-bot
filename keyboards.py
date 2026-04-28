from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(lang: str = 'ar') -> ReplyKeyboardMarkup:
    """Get main menu keyboard based on language"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'ar':
        buttons = [
            KeyboardButton('🎉 الطلبات المجانية'),
            KeyboardButton('💰 طلبات الشراء'),
            KeyboardButton('🎮 المودات'),
            KeyboardButton('📝 الشكاوى'),
            KeyboardButton('⭐ تقييم البوت'),
            KeyboardButton('🌍 تغيير اللغة')
        ]
    else:
        buttons = [
            KeyboardButton('🎉 Free Requests'),
            KeyboardButton('💰 Purchase Requests'),
            KeyboardButton('🎮 Mods'),
            KeyboardButton('📝 Complaints'),
            KeyboardButton('⭐ Rate Bot'),
            KeyboardButton('🌍 Change Language')
        ]
    
    markup.add(*buttons)
    return markup

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Get admin panel keyboard (Arabic only)"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton('📊 الإحصائيات'),
        KeyboardButton('📢 إذاعة'),
        KeyboardButton('🚫 حظر مستخدم'),
        KeyboardButton('✅ فك حظر'),
        KeyboardButton('📋 الطلبات'),
        KeyboardButton('📝 التذاكر'),
        KeyboardButton('📜 السجلات')
    ]
    markup.add(*buttons)
    return markup

def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Get yes/no inline keyboard"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ نعم", callback_data="yes"),
        InlineKeyboardButton("❌ لا", callback_data="no")
    )
    return markup

def get_order_admin_keyboard(order_number: str, user_id: int) -> InlineKeyboardMarkup:
    """Get admin order action keyboard"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ تم التنفيذ", callback_data=f"done_{order_number}_{user_id}"),
        InlineKeyboardButton("🔄 جاري التنفيذ", callback_data=f"exec_{order_number}_{user_id}")
    )
    markup.add(
        InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_{order_number}_{user_id}"),
        InlineKeyboardButton("💬 رد", callback_data=f"chat_{order_number}_{user_id}")
    )
    markup.add(
        InlineKeyboardButton("🚫 حظر", callback_data=f"ban_{order_number}_{user_id}")
    )
    return markup

def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Get rating keyboard (1-5 stars)"""
    markup = InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        markup.insert(InlineKeyboardButton("⭐" * i, callback_data=f"rate_{i}"))
    return markup

def get_support_rating_keyboard() -> InlineKeyboardMarkup:
    """Get support rating keyboard (1-5 stars)"""
    markup = InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        markup.insert(InlineKeyboardButton("⭐" * i, callback_data=f"support_rate_{i}"))
    return markup

def get_live_chat_keyboard() -> InlineKeyboardMarkup:
    """Get live chat keyboard"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔒 إنهاء المحادثة", callback_data="end_chat"))
    return markup

def get_contact_button(lang: str = 'ar') -> InlineKeyboardMarkup:
    """Get contact button based on language"""
    text = "💬 تواصل بنا" if lang == 'ar' else "💬 Contact Us"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text, callback_data="contact_us"))
    return markup

def get_back_button(lang: str = 'ar') -> InlineKeyboardMarkup:
    """Get back button based on language"""
    text = "🔙 رجوع" if lang == 'ar' else "🔙 Back"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text, callback_data="back_main"))
    return markup