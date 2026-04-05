from datetime import datetime, timedelta
from typing import Optional
import re
import pytz
import dateparser
from timezonefinder import TimezoneFinder


def format_date(dt: datetime, user_tz: str) -> str:
    """
    Форматирует дату в читаемый вид:
    - "Сегодня, 18:00"
    - "Завтра, 10:00"
    - "6 апреля, 14:00"
    """
    tz = pytz.timezone(user_tz)
    
    # Если datetime без часового пояса (naive), предполагаем что это UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    dt_local = dt.astimezone(tz)
    now = datetime.now(tz)
    
    # Проверяем, сегодня ли
    if dt_local.date() == now.date():
        return f"Сегодня, {dt_local.strftime('%H:%M')}"
    
    # Проверяем, завтра ли
    tomorrow = now.date() + timedelta(days=1)
    if dt_local.date() == tomorrow:
        return f"Завтра, {dt_local.strftime('%H:%M')}"
    
    # Иначе - полная дата
    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    
    day = dt_local.day
    month = months[dt_local.month - 1]
    time_str = dt_local.strftime('%H:%M')
    
    return f"{day} {month}, {time_str}"


def parse_date(text: str, user_tz: str) -> Optional[datetime]:
    """
    Парсит дату из текста пользователя
    Примеры: "завтра 18:00", "06.04.2026 18:00"
    """
    settings = {
        'TIMEZONE': user_tz,
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': True
    }
    
    parsed = dateparser.parse(text, languages=['ru'], settings=settings)
    return parsed


def parse_time(text: str) -> Optional[tuple]:
    """
    Парсит время из текста (например: "18:00", "18-00", "1800")
    Возвращает (hours, minutes) или None
    """
    # Паттерны для времени
    patterns = [
        r'(\d{1,2}):(\d{2})',  # 18:00
        r'(\d{1,2})-(\d{2})',  # 18-00
        r'(\d{2})(\d{2})',     # 1800
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return (hours, minutes)
    
    return None


def parse_reminder_offset(text: str) -> Optional[dict]:
    """
    Парсит время напоминания из текста
    Примеры: "за 2 часа", "за 3 дня"
    Возвращает {'offset_type': 'hours', 'offset_value': 2} или None
    """
    pattern = r'за\s+(\d+)\s+(час|часа|часов|день|дня|дней)'
    match = re.search(pattern, text.lower())
    
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        
        if 'час' in unit:
            return {'offset_type': 'hours', 'offset_value': value}
        else:
            return {'offset_type': 'days', 'offset_value': value}
    
    return None


def get_timezone_from_location(latitude: float, longitude: float) -> Optional[str]:
    """
    Определяет часовой пояс по координатам
    """
    tf = TimezoneFinder()
    timezone = tf.timezone_at(lat=latitude, lng=longitude)
    return timezone


def get_timezone_name(tz_str: str) -> str:
    """
    Возвращает читаемое название часового пояса
    """
    tz_names = {
        'Europe/Moscow': 'МСК (UTC+3)',
        'Europe/Samara': 'Самара (UTC+4)',
        'Asia/Yekaterinburg': 'Екатеринбург (UTC+5)',
        'Asia/Omsk': 'Омск (UTC+6)',
        'Asia/Novosibirsk': 'Новосибирск (UTC+7)',
        'Asia/Krasnoyarsk': 'Красноярск (UTC+7)',
        'Asia/Irkutsk': 'Иркутск (UTC+8)',
        'Asia/Yakutsk': 'Якутск (UTC+9)',
        'Asia/Vladivostok': 'Владивосток (UTC+10)',
        'Asia/Magadan': 'Магадан (UTC+11)',
        'Asia/Kamchatka': 'Камчатка (UTC+12)',
    }
    
    return tz_names.get(tz_str, tz_str)


def calculate_next_recurring_date(current_date: datetime, pattern: str) -> datetime:
    """
    Вычисляет следующую дату для повторяющейся задачи
    """
    if pattern == 'daily':
        return current_date + timedelta(days=1)
    elif pattern == 'weekly':
        return current_date + timedelta(days=7)
    elif pattern == 'monthly':
        return current_date + timedelta(days=30)
    else:
        return current_date


def get_priority_emoji(priority: str) -> str:
    """
    Возвращает эмодзи для приоритета
    """
    priority_emojis = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    }
    return priority_emojis.get(priority, '⚪')


def format_reminder_template(template: dict) -> str:
    """
    Форматирует шаблон напоминания в читаемый вид
    """
    reminder_hour = template['reminder_hour']
    return f"В {reminder_hour:02d}:00"
