import logging
import sys
import asyncio
import signal
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from config import BOT_TOKEN, ADMIN_ID, LOG_LEVEL, LOG_FORMAT
from database import db
from keyboards import get_main_keyboard
from handlers import (
    register_start_handlers,
    register_admin_handlers,
    register_free_orders_handlers,
    register_paid_orders_handlers,
    register_mods_handlers,
    register_support_handlers,
    register_rating_handlers,
    register_language_handlers,
    register_broadcast_handlers,
    register_ban_handlers
)
from utils.timeout_manager import timeout_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot once
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Set bot instance in timeout manager
timeout_manager.set_bot(bot)

# Flag to prevent duplicate handler registration
_handlers_registered = False

def register_all_handlers():
    """Register all handlers only once"""
    global _handlers_registered
    
    if _handlers_registered:
        logger.info("Handlers already registered, skipping")
        return
    
    try:
        register_start_handlers(dp)
        register_admin_handlers(dp)
        register_free_orders_handlers(dp)
        register_paid_orders_handlers(dp)
        register_mods_handlers(dp)
        register_support_handlers(dp)
        register_rating_handlers(dp)
        register_language_handlers(dp)
        register_broadcast_handlers(dp)
        register_ban_handlers(dp)
        
        _handlers_registered = True
        logger.info("All handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register handlers: {e}")
        raise

# Global error handler
async def error_handler(update, exception):
    """Global error handler for all exceptions"""
    logger.error(f"Error in update {update}: {exception}", exc_info=True)
    
    try:
        if hasattr(update, 'message') and update.message:
            user_id = update.message.chat.id
            lang = db.get_user_language(user_id)
            await bot.send_message(
                user_id,
                "⚠️ عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.\n⚠️ Sorry, an error occurred. Please try again.",
                reply_markup=get_main_keyboard(lang)
            )
        elif hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("⚠️ حدث خطأ، حاول مرة أخرى", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

dp.register_errors_handler(error_handler)

# Rate limit check
async def rate_limit_check(message: types.Message) -> bool:
    """Check rate limit for messages"""
    from utils.helpers import is_rate_limited
    user_id = message.from_user.id
    
    if is_rate_limited(user_id, 'global', limit=30, window=60):
        lang = db.get_user_language(user_id)
        await message.answer(
            "⚠️ أرسلت رسائل كثيرة، انتظر قليلاً" if lang == 'ar' else "⚠️ Too many messages, please wait",
            reply_markup=get_main_keyboard(lang)
        )
        return False
    return True

# Back button handler
@dp.callback_query_handler(lambda c: c.data == 'back_main', state='*')
async def back_main(callback_query: types.CallbackQuery):
    """Handle back button"""
    try:
        user_id = callback_query.from_user.id
        lang = db.get_user_language(user_id)
        db.update_last_active(user_id)

        await callback_query.message.edit_text(
            "اهلاً بك في متجر Shop Crowns 🎉🎁\nاختر من القائمة 👇" if lang == 'ar' else "Welcome to Shop Crowns 🎉🎁\nChoose from the menu 👇",
            reply_markup=None
        )
        await callback_query.message.answer(
            "اهلاً بك في متجر Shop Crowns 🎉🎁\nاختر من القائمة 👇" if lang == 'ar' else "Welcome to Shop Crowns 🎉🎁\nChoose from the menu 👇",
            reply_markup=get_main_keyboard(lang)
        )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Error in back_main: {e}")
        await callback_query.answer("⚠️ خطأ، حاول مرة أخرى", show_alert=True)

# Fallback handler
@dp.message_handler()
async def fallback_handler(message: types.Message):
    """Fallback handler for unhandled messages"""
    try:
        user_id = message.from_user.id
        lang = db.get_user_language(user_id)
        db.update_last_active(user_id)
        
        if not await rate_limit_check(message):
            return
        
        if db.is_user_banned(user_id):
            await message.answer(
                "🚫 تم حظرك من البوت" if lang == 'ar' else "🚫 You are banned",
                parse_mode='Markdown'
            )
            return

        await message.answer(
            "اهلاً بك في متجر Shop Crowns 🎉🎁\nاختر من القائمة 👇" if lang == 'ar' else "Welcome to Shop Crowns 🎉🎁\nChoose from the menu 👇",
            reply_markup=get_main_keyboard(lang)
        )
    except Exception as e:
        logger.error(f"Error in fallback_handler: {e}")

# Startup and shutdown events
async def on_startup(dp):
    """Called when bot starts"""
    logger.info("🚀 Shop Crowns Avakin Bot started")
    logger.info(f"Bot token configured: {'Yes' if BOT_TOKEN else 'No'}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    
    try:
        db.update_last_active(ADMIN_ID)
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    await bot.send_message(ADMIN_ID, "✅ **البوت شغال بكفاءة عالية**\n\n"
                                      "📊 **المراقبة نشطة**\n"
                                      "⏰ **المهلات تعمل**\n"
                                      "🔒 **الأمان مفعل**", parse_mode='Markdown')

async def on_shutdown(dp):
    """Called when bot shuts down"""
    logger.info("🛑 Shop Crowns Avakin Bot shutting down")
    await timeout_manager.clear_all_timeouts()
    db.close()
    await bot.close()
    logger.info("Bot shutdown complete")

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(on_shutdown(None))
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register all handlers
register_all_handlers()

# Main entry point
if __name__ == '__main__':
    try:
        logger.info("Starting Shop Crowns Avakin Bot...")
        executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)