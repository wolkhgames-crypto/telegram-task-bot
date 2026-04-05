import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')

# PostgreSQL Database
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'sslmode': os.getenv('DB_SSLMODE', 'require')
}

# Логирование
LOG_LEVEL = 'INFO'
LOG_FILE = 'bot.log'

# Пагинация
TASKS_PER_PAGE = 10

# Дефолтные времена напоминаний (создаются при регистрации пользователя)
# Напоминания будут отправляться в эти часы в день дедлайна
DEFAULT_REMINDER_TIMES = [
    7,   # 7:00 утра
    14,  # 14:00 дня
    19,  # 19:00 вечера
]
