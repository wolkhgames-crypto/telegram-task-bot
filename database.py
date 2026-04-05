import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import pytz

from config import DB_CONFIG, DEFAULT_REMINDER_TIMES

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL базой данных"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False) -> Optional[List[Dict]]:
        """Выполнение SQL запроса"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                    return [dict(row) for row in result]
                self.conn.commit()
                return None
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_query_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Выполнение SQL запроса с возвратом одной строки"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    # ==================== USERS ====================
    
    def create_user(self, user_id: int, username: str, timezone: str) -> bool:
        """Создание нового пользователя"""
        query = """
            INSERT INTO users (user_id, username, timezone)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """
        try:
            self.execute_query(query, (user_id, username, timezone))
            
            # Создаем дефолтные времена напоминаний (7:00, 14:00, 19:00)
            for hour in DEFAULT_REMINDER_TIMES:
                self.create_reminder_template(user_id, hour)
            
            logger.info(f"User {user_id} created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        query = "SELECT * FROM users WHERE user_id = %s"
        return self.execute_query_one(query, (user_id,))
    
    def update_user_timezone(self, user_id: int, timezone: str) -> bool:
        """Обновление часового пояса пользователя"""
        query = "UPDATE users SET timezone = %s WHERE user_id = %s"
        try:
            self.execute_query(query, (timezone, user_id))
            logger.info(f"Timezone updated for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update timezone: {e}")
            return False
    
    # ==================== TASKS ====================
    
    def create_task(self, user_id: int, title: str, due_date: datetime, 
                    priority: str = 'medium', is_recurring: bool = False, 
                    recurring_pattern: Optional[str] = None) -> Optional[int]:
        """Создание новой задачи"""
        query = """
            INSERT INTO tasks (user_id, title, due_date, priority, is_recurring, recurring_pattern)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        try:
            # Ensure due_date is UTC aware before saving
            if due_date.tzinfo is None:
                due_date = pytz.UTC.localize(due_date)
            due_date_utc = due_date.astimezone(pytz.UTC)
            
            with self.conn.cursor() as cursor:
                cursor.execute(query, (user_id, title, due_date_utc, priority, is_recurring, recurring_pattern))
                task_id = cursor.fetchone()[0]
                self.conn.commit()
                logger.info(f"Task {task_id} created for user {user_id}")
                return task_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create task: {e}")
            return None
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """Получение задачи по ID"""
        query = "SELECT * FROM tasks WHERE id = %s"
        return self.execute_query_one(query, (task_id,))
    
    def get_user_tasks(self, user_id: int, is_completed: bool = False, 
                       limit: int = None, offset: int = 0) -> List[Dict]:
        """Получение задач пользователя"""
        query = """
            SELECT * FROM tasks 
            WHERE user_id = %s AND is_completed = %s 
            ORDER BY due_date ASC
        """
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        result = self.execute_query(query, (user_id, is_completed), fetch=True)
        return result or []
    
    def get_tasks_count(self, user_id: int, is_completed: bool = False) -> int:
        """Получение количества задач пользователя"""
        query = "SELECT COUNT(*) as count FROM tasks WHERE user_id = %s AND is_completed = %s"
        result = self.execute_query_one(query, (user_id, is_completed))
        return result['count'] if result else 0
    
    def get_today_tasks(self, user_id: int, start_of_day: datetime, end_of_day: datetime) -> List[Dict]:
        """Получение задач на сегодня"""
        query = """
            SELECT * FROM tasks 
            WHERE user_id = %s AND is_completed = false 
            AND due_date BETWEEN %s AND %s
            ORDER BY due_date ASC
        """
        result = self.execute_query(query, (user_id, start_of_day, end_of_day), fetch=True)
        return result or []
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """Обновление задачи"""
        allowed_fields = ['title', 'due_date', 'priority', 'is_recurring', 'recurring_pattern']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s"
        
        try:
            self.execute_query(query, tuple(values))
            logger.info(f"Task {task_id} updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return False
    
    def complete_task(self, task_id: int) -> bool:
        """Отметить задачу как выполненную"""
        query = "UPDATE tasks SET is_completed = true, completed_at = NOW() WHERE id = %s"
        try:
            self.execute_query(query, (task_id,))
            logger.info(f"Task {task_id} marked as completed")
            return True
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False
    
    def restore_task(self, task_id: int, new_due_date: Optional[datetime] = None) -> bool:
        """Восстановить выполненную задачу"""
        if new_due_date:
            query = "UPDATE tasks SET is_completed = false, completed_at = NULL, due_date = %s WHERE id = %s"
            params = (new_due_date, task_id)
        else:
            query = "UPDATE tasks SET is_completed = false, completed_at = NULL WHERE id = %s"
            params = (task_id,)
        
        try:
            self.execute_query(query, params)
            logger.info(f"Task {task_id} restored")
            return True
        except Exception as e:
            logger.error(f"Failed to restore task: {e}")
            return False
    
    def delete_task(self, task_id: int) -> bool:
        """Удаление задачи"""
        query = "DELETE FROM tasks WHERE id = %s"
        try:
            self.execute_query(query, (task_id,))
            logger.info(f"Task {task_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            return False
    
    # ==================== REMINDERS ====================
    
    def create_reminder(self, task_id: int, remind_at: datetime) -> Optional[int]:
        """Создание напоминания"""
        query = """
            INSERT INTO reminders (task_id, remind_at)
            VALUES (%s, %s)
            RETURNING id
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (task_id, remind_at))
                reminder_id = cursor.fetchone()[0]
                self.conn.commit()
                logger.info(f"Reminder {reminder_id} created for task {task_id}")
                return reminder_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create reminder: {e}")
            return None
    
    def get_task_reminders(self, task_id: int) -> List[Dict]:
        """Получение напоминаний для задачи"""
        query = "SELECT * FROM reminders WHERE task_id = %s ORDER BY remind_at ASC"
        result = self.execute_query(query, (task_id,), fetch=True)
        return result or []
    
    def get_pending_reminders(self) -> List[Dict]:
        """Получение неотправленных напоминаний"""
        # Используем текущее время UTC из Python для точности
        now_utc = datetime.now(pytz.UTC)
        
        query = """
            SELECT r.id, r.task_id, r.remind_at, t.user_id, t.title, t.due_date, t.priority
            FROM reminders r
            JOIN tasks t ON r.task_id = t.id
            WHERE r.remind_at <= %s
            AND r.is_sent = false
            AND t.is_completed = false
        """
        result = self.execute_query(query, (now_utc,), fetch=True)
        return result or []
    
    def mark_reminder_sent(self, reminder_id: int) -> bool:
        """Отметить напоминание как отправленное"""
        query = "UPDATE reminders SET is_sent = true WHERE id = %s"
        try:
            self.execute_query(query, (reminder_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to mark reminder as sent: {e}")
            return False
    
    def delete_task_reminders(self, task_id: int) -> bool:
        """Удаление всех напоминаний задачи"""
        query = "DELETE FROM reminders WHERE task_id = %s"
        try:
            self.execute_query(query, (task_id,))
            logger.info(f"Reminders deleted for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete reminders: {e}")
            return False
    
    def delete_reminder(self, reminder_id: int) -> bool:
        """Удаление конкретного напоминания"""
        query = "DELETE FROM reminders WHERE id = %s"
        try:
            self.execute_query(query, (reminder_id,))
            logger.info(f"Reminder {reminder_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete reminder: {e}")
            return False
    
    # ==================== REMINDER TEMPLATES ====================
    
    def create_reminder_template(self, user_id: int, reminder_hour: int) -> Optional[int]:
        """Создание шаблона напоминания (конкретный час)"""
        query = """
            INSERT INTO reminder_templates (user_id, reminder_hour)
            VALUES (%s, %s)
            RETURNING id
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (user_id, reminder_hour))
                template_id = cursor.fetchone()[0]
                self.conn.commit()
                logger.info(f"Reminder template {template_id} created for user {user_id}")
                return template_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create reminder template: {e}")
            return None
    
    def get_user_reminder_templates(self, user_id: int) -> List[Dict]:
        """Получение шаблонов напоминаний пользователя"""
        query = """
            SELECT * FROM reminder_templates 
            WHERE user_id = %s AND is_active = true
            ORDER BY reminder_hour
        """
        result = self.execute_query(query, (user_id,), fetch=True)
        return result or []
    
    def delete_reminder_template(self, template_id: int) -> bool:
        """Удаление шаблона напоминания"""
        query = "DELETE FROM reminder_templates WHERE id = %s"
        try:
            self.execute_query(query, (template_id,))
            logger.info(f"Reminder template {template_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete reminder template: {e}")
            return False
    
    def create_reminders_from_templates(self, task_id: int, user_id: int, due_date: datetime) -> bool:
        """Создание напоминаний для задачи на основе шаблонов пользователя
        
        Создает напоминания:
        1. В конкретное время в день дедлайна (7:00, 14:00, 19:00)
        2. В момент дедлайна
        """
        templates = self.get_user_reminder_templates(user_id)
        
        # Получаем пользователя для часового пояса
        user = self.get_user(user_id)
        if not user:
            return False
        
        user_tz = pytz.timezone(user['timezone'])
        
        # Конвертируем due_date в локальное время пользователя
        due_date_local = due_date.astimezone(user_tz)
        
        # Получаем дату дедлайна (без времени)
        due_date_only = due_date_local.date()
        
        # Создаем напоминания в конкретное время в день дедлайна
        for template in templates:
            reminder_hour = template['reminder_hour']
            
            # Создаем datetime для напоминания в локальном времени
            remind_datetime_local = user_tz.localize(
                datetime.combine(due_date_only, datetime.min.time().replace(hour=reminder_hour, minute=0))
            )
            
            # Конвертируем в UTC для сохранения
            remind_at_utc = remind_datetime_local.astimezone(pytz.UTC)
            
            # Создаем напоминание только если:
            # 1. Время еще не прошло
            # 2. Время напоминания раньше времени дедлайна
            now_utc = datetime.now(pytz.UTC)
            if remind_at_utc > now_utc and remind_at_utc < due_date:
                self.create_reminder(task_id, remind_at_utc)
        
        # Создаем напоминание в момент дедлайна
        now_utc = datetime.now(pytz.UTC)
        if due_date > now_utc:
            self.create_reminder(task_id, due_date)
        
        return True
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Глобальный экземпляр базы данных
db = Database()
