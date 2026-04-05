from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
import logging

from database import db
from utils import format_date, get_priority_emoji
from keyboards import get_reminder_notification_keyboard

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_reminders(bot: Bot):
    """Проверяет и отправляет напоминания"""
    try:
        # Получаем все неотправленные напоминания
        reminders = db.get_pending_reminders()
        
        if not reminders:
            return
        
        logger.info(f"Found {len(reminders)} pending reminders")
        
        for reminder in reminders:
            try:
                await send_reminder_notification(bot, reminder)
                # Помечаем напоминание как отправленное
                db.mark_reminder_sent(reminder['id'])
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder['id']}: {e}")
    
    except Exception as e:
        logger.error(f"Error in check_reminders: {e}")


async def send_reminder_notification(bot: Bot, reminder: dict):
    """Отправляет уведомление о напоминании"""
    user_id = reminder['user_id']
    task_id = reminder['task_id']
    title = reminder['title']
    due_date = reminder['due_date']
    priority = reminder['priority']
    
    # Получаем часовой пояс пользователя
    user = db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return
    
    user_tz = user['timezone']
    
    # Форматируем дату
    formatted_date = format_date(due_date, user_tz)
    priority_emoji = get_priority_emoji(priority)
    
    text = f"""🔔 Напоминание!

Задача: {title}
Дедлайн: {formatted_date}
Приоритет: {priority_emoji}"""
    
    # Клавиатура с действиями
    keyboard = get_reminder_notification_keyboard(task_id)
    
    try:
        await bot.send_message(user_id, text, reply_markup=keyboard)
        logger.info(f"Reminder sent to user {user_id} for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to send message to user {user_id}: {e}")
        raise


def start_scheduler(bot: Bot):
    """Запуск планировщика напоминаний"""
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(minutes=1),
        args=[bot],
        id='check_reminders',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Остановка планировщика"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
