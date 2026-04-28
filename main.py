import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from config import BOT_TOKEN, ADMIN_ID
from database import db
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

timeout_manager.set_bot(bot)

# Register all handlers
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

logger.info("All handlers registered successfully")


async def on_startup(dp):
    logger.info("🚀 Bot started")
    await bot.send_message(ADMIN_ID, "✅ البوت شغال")


async def on_shutdown(dp):
    logger.info("🛑 Bot shutting down")
    await timeout_manager.clear_all_timeouts()
    db.close()
    await bot.close()


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
