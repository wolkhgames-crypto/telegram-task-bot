import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router
from scheduler import start_scheduler, stop_scheduler
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Bot is starting...")
    
    # Запускаем планировщик напоминаний
    start_scheduler(bot)
    logger.info("Scheduler started")
    
    logger.info("Bot started successfully!")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Bot is shutting down...")
    
    # Останавливаем планировщик
    stop_scheduler()
    
    # Закрываем соединение с БД
    db.close()
    
    logger.info("Bot stopped")


async def main():
    """Главная функция запуска бота"""
    
    # Проверка токена
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("BOT_TOKEN not set! Please set it in .env file")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутера
    dp.include_router(router)
    
    try:
        # Запуск бота
        await on_startup(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error while running bot: {e}")
    finally:
        await on_shutdown()
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
