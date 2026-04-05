-- Инициализация базы данных для Telegram Task Bot

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    timezone VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица задач
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_date TIMESTAMP NOT NULL,
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    is_completed BOOLEAN DEFAULT false,
    is_recurring BOOLEAN DEFAULT false,
    recurring_pattern VARCHAR(20) CHECK (recurring_pattern IN ('daily', 'weekly', 'monthly')),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_user_completed ON tasks(user_id, is_completed);
CREATE INDEX IF NOT EXISTS idx_user_due_date ON tasks(user_id, due_date);

-- Таблица напоминаний
CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    remind_at TIMESTAMP NOT NULL,
    is_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индекс для быстрой проверки напоминаний
CREATE INDEX IF NOT EXISTS idx_remind_at_sent ON reminders(remind_at, is_sent);

-- Таблица шаблонов напоминаний
CREATE TABLE IF NOT EXISTS reminder_templates (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    offset_type VARCHAR(10) NOT NULL CHECK (offset_type IN ('hours', 'days')),
    offset_value INT NOT NULL CHECK (offset_value > 0),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индекс для получения активных шаблонов пользователя
CREATE INDEX IF NOT EXISTS idx_user_templates ON reminder_templates(user_id, is_active);
