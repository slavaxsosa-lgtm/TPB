import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import config
from bot.mock_sheets import MockSheetsManager as SheetsManager
from bot.scheduler import BroadcastScheduler
from bot.handlers.common import register_common_handlers
from bot.handlers.tutor import register_tutor_handlers
from bot.handlers.admin import register_admin_handlers
from bot.handlers.admin_lists import register_admin_list_handlers
from bot.handlers.buttons import register_button_handlers

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger=logging.getLogger(__name__)

async def main():
    logger.info("Bot starting...")
    try:
        bot=Bot(token=config.bot_token)
        storage=MemoryStorage()
        dp=Dispatcher(storage=storage)
        sheets_manager=SheetsManager()
        logger.info("Connected to Mock Sheets (for testing)")
        broadcast_scheduler=None
        if config.group_ids:
            broadcast_scheduler=BroadcastScheduler(bot, config.group_ids)
            broadcast_scheduler.start()
            logger.info(f"Broadcast scheduler started for {len(config.group_ids)} groups")
        else:
            logger.warning("GROUP_IDS not configured, auto-broadcasts disabled")
        register_common_handlers(dp, sheets_manager, bot)
        register_tutor_handlers(dp, sheets_manager, bot)
        register_admin_handlers(dp, sheets_manager, bot, broadcast_scheduler)
        register_admin_list_handlers(dp, sheets_manager, bot)
        register_button_handlers(dp, sheets_manager, bot)
        logger.info("Handlers registered")
        logger.info("Bot started and ready")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Stop signal received (Ctrl+C)")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        raise
    finally:
        if 'broadcast_scheduler' in locals() and broadcast_scheduler:
            broadcast_scheduler.stop()
        logger.info("Bot stopped")

if __name__=='__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        sys.exit(1)
