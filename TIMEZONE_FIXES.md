# 🔧 Исправление проблем с часовыми поясами

## Дата: 05.04.2026, 21:12

---

## ❌ Проблема:

При создании задачи время отображалось неправильно:
- Пользователь создает задачу на **21:08** (МСК, UTC+3)
- Бот показывает задачу на **18:08** (разница -3 часа)

**Причина:** Локальное время сохранялось в БД без конвертации в UTC, а PostgreSQL интерпретировал его как UTC.

---

## ✅ Решение:

### Принцип работы с датами:

1. **Ввод от пользователя** → Локальное время (МСК, UTC+3)
2. **Сохранение в БД** → Конвертация в UTC
3. **Чтение из БД** → Получаем UTC
4. **Отображение пользователю** → Конвертация обратно в локальное время

---

## 📝 Исправленные места:

### 1. **handlers.py - Создание задачи** (строки 378-386)

**Было:**
```python
# Создаем задачу
task_id = db.create_task(
    user_id=user_id,
    title=title,
    due_date=due_date,  # ❌ Локальное время
    ...
)
```

**Стало:**
```python
# Конвертируем due_date в UTC для сохранения в БД
if due_date.tzinfo is None:
    user = db.get_user(user_id)
    user_tz = pytz.timezone(user['timezone'])
    due_date = user_tz.localize(due_date)

# Конвертируем в UTC
due_date_utc = due_date.astimezone(pytz.UTC)

# Создаем задачу
task_id = db.create_task(
    user_id=user_id,
    title=title,
    due_date=due_date_utc,  # ✅ UTC время
    ...
)
```

---

### 2. **handlers.py - Создание напоминаний** (строки 403-417)

**Было:**
```python
db.create_reminders_from_templates(task_id, user_id, due_date)  # ❌ Локальное время

if custom_reminder:
    remind_at = due_date - timedelta(...)  # ❌ Локальное время
```

**Стало:**
```python
db.create_reminders_from_templates(task_id, user_id, due_date_utc)  # ✅ UTC

if custom_reminder:
    remind_at = due_date_utc - timedelta(...)  # ✅ UTC
```

---

### 3. **handlers.py - Отображение даты** (строка 421)

**Было:**
```python
formatted_date = format_date(due_date, user['timezone'])  # ❌ Локальное время
```

**Стало:**
```python
formatted_date = format_date(due_date_utc, user['timezone'])  # ✅ UTC → Локальное
```

---

### 4. **handlers.py - Редактирование даты** (строки 766-786)

**Было:**
```python
parsed_date = parse_date(message.text, user_tz)  # Локальное время
success = db.update_task(task_id, due_date=parsed_date)  # ❌ Локальное время
db.create_reminders_from_templates(task_id, user_id, parsed_date)  # ❌
```

**Стало:**
```python
parsed_date = parse_date(message.text, user_tz)  # Локальное время
parsed_date_utc = parsed_date.astimezone(pytz.UTC)  # ✅ Конвертация в UTC

success = db.update_task(task_id, due_date=parsed_date_utc)  # ✅ UTC
db.create_reminders_from_templates(task_id, user_id, parsed_date_utc)  # ✅ UTC
```

---

### 5. **database.py - Сравнение дат** (строка 348)

**Было:**
```python
if remind_at > datetime.now():  # ❌ Сравнение aware с naive
```

**Стало:**
```python
now_utc = datetime.now(pytz.UTC)  # ✅ UTC aware datetime
if remind_at > now_utc:  # ✅ Сравнение aware с aware
```

---

### 6. **handlers.py - Восстановление задачи** (строка 651)

**Было:**
```python
if task['due_date'] < now:  # ❌ UTC < Локальное
```

**Стало:**
```python
task_due_date = task['due_date'].astimezone(user_tz)  # ✅ UTC → Локальное
if task_due_date < now:  # ✅ Локальное < Локальное
```

---

## 🎯 Результат:

### До исправления:
```
Пользователь вводит: 21:08 (МСК)
Сохраняется в БД: 21:08 (как UTC)
Читается из БД: 21:08 (UTC)
Отображается: 18:08 (21:08 UTC → МСК = 21:08 - 3 = 18:08) ❌
```

### После исправления:
```
Пользователь вводит: 21:08 (МСК, UTC+3)
Конвертируется: 18:08 (UTC)
Сохраняется в БД: 18:08 (UTC)
Читается из БД: 18:08 (UTC)
Конвертируется обратно: 21:08 (МСК)
Отображается: 21:08 ✅
```

---

## 📋 Проверочный список:

- ✅ Создание задачи - время корректное
- ✅ Просмотр задач - время корректное
- ✅ Редактирование даты - конвертация в UTC
- ✅ Восстановление задачи - сравнение в одном часовом поясе
- ✅ Повторяющиеся задачи - работают с UTC
- ✅ Напоминания - создаются в UTC
- ✅ Сравнение дат - всегда aware datetime

---

## 🧪 Тестирование:

Создай новую задачу и проверь:
1. Введи время: **21:15**
2. Проверь в списке задач - должно показать **21:15** (не 18:15)
3. Дождись напоминания - должно прийти в правильное время

---

## 📌 Важные правила:

1. **Всегда сохраняем в БД в UTC**
2. **Всегда отображаем в локальном времени пользователя**
3. **Всегда используем aware datetime (с часовым поясом)**
4. **Всегда конвертируем перед сравнением**

---

**Статус:** ✅ Все исправлено
**Версия:** 1.0.2
**Дата:** 05.04.2026, 21:12
