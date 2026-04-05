from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, Location
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import pytz
import logging
import math

from states import Setup, CreateTask, EditTask, Settings
from keyboards import (
    get_main_menu, get_location_keyboard, get_timezone_keyboard,
    get_date_quick_buttons, get_priority_keyboard, get_recurring_keyboard,
    get_custom_reminder_keyboard, get_task_actions_keyboard,
    get_pagination_keyboard, get_delete_confirmation_keyboard,
    get_edit_menu_keyboard, get_completed_task_actions_keyboard,
    get_settings_keyboard, get_reminder_actions_keyboard,
    get_back_to_menu_keyboard, get_timezone_confirmation_keyboard
)
from database import db
from utils import (
    format_date, parse_date, parse_time, parse_reminder_offset,
    get_timezone_from_location, get_timezone_name, calculate_next_recurring_date,
    get_priority_emoji, format_reminder_template
)
from config import TASKS_PER_PAGE

logger = logging.getLogger(__name__)

router = Router()


# ==================== КОМАНДА /start ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Проверяем, есть ли пользователь в БД
    user = db.get_user(user_id)
    
    if user:
        # Пользователь уже зарегистрирован
        await message.answer(
            f"С возвращением, {username}! 👋\n\n"
            "Выбери действие из меню:",
            reply_markup=get_main_menu()
        )
    else:
        # Новый пользователь - запускаем регистрацию
        await message.answer(
            f"Привет, {username}! 👋\n\n"
            "Я помогу тебе управлять задачами и напоминаниями.\n\n"
            "Для начала мне нужно узнать твой часовой пояс.\n"
            "Поделись своей геолокацией, и я определю его автоматически.",
            reply_markup=get_location_keyboard()
        )
        await state.set_state(Setup.waiting_for_timezone)


@router.message(Setup.waiting_for_timezone, F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка геолокации для определения часового пояса"""
    location: Location = message.location
    
    # Определяем часовой пояс по координатам
    timezone = get_timezone_from_location(location.latitude, location.longitude)
    
    if not timezone:
        await message.answer(
            "❌ Не удалось определить часовой пояс по геолокации.\n"
            "Выбери часовой пояс вручную:",
            reply_markup=get_timezone_keyboard()
        )
        return
    
    # Сохраняем в FSM для подтверждения
    await state.update_data(timezone=timezone)
    
    tz_name = get_timezone_name(timezone)
    await message.answer(
        f"Твой часовой пояс: {tz_name}\n\nВерно?",
        reply_markup=get_timezone_confirmation_keyboard(timezone)
    )


@router.message(Setup.waiting_for_timezone, F.text == "✏️ Ввести вручную")
async def manual_timezone_input(message: Message):
    """Ручной ввод часового пояса"""
    await message.answer(
        "Выбери свой часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )


@router.callback_query(F.data.startswith("tz_"))
async def process_timezone_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора часового пояса"""
    timezone = callback.data.replace("tz_", "")
    await state.update_data(timezone=timezone)
    
    tz_name = get_timezone_name(timezone)
    await callback.message.edit_text(
        f"Твой часовой пояс: {tz_name}\n\nВерно?",
        reply_markup=get_timezone_confirmation_keyboard(timezone)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_tz_"))
async def confirm_timezone(callback: CallbackQuery, state: FSMContext):
    """Подтверждение часового пояса и создание пользователя"""
    timezone = callback.data.replace("confirm_tz_", "")
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    # Создаем пользователя в БД
    success = db.create_user(user_id, username, timezone)
    
    if success:
        await callback.message.edit_text(
            "✅ Регистрация завершена!\n\n"
            "Теперь ты можешь создавать задачи и управлять ими."
        )
        await callback.message.answer(
            "Выбери действие из меню:",
            reply_markup=get_main_menu()
        )
        await state.clear()
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при регистрации. Попробуй еще раз /start"
        )
    
    await callback.answer()


@router.callback_query(F.data == "change_tz")
async def change_timezone_from_confirmation(callback: CallbackQuery):
    """Изменение часового пояса из подтверждения"""
    await callback.message.edit_text(
        "Выбери свой часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )
    await callback.answer()


# ==================== КОМАНДА /help ====================

@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message, state: FSMContext):
    """Обработчик команды /help"""
    await state.clear()  # Очищаем FSM состояние
    help_text = """📖 Справка по боту

🔹 Основные функции:
• ➕ Новая задача - создать новую задачу
• 📋 Мои задачи - посмотреть все активные задачи
• 📅 Сегодня - задачи на сегодня
• ✅ Выполненные - история выполненных задач
• ⚙️ Настройки - настройки напоминаний и часового пояса

🔹 Создание задачи:
При создании задачи нужно указать название и дату/время.
Примеры ввода даты:
• "завтра 18:00"
• "06.04.2026 18:00"
• Или выбрать быструю кнопку (Сегодня/Завтра/Через неделю)

🔹 Приоритеты:
🔴 Высокий - важные задачи
🟡 Средний - обычные задачи
🟢 Низкий - не срочные задачи

🔹 Повторяющиеся задачи:
Можно настроить автоматическое создание задачи после выполнения:
• Ежедневно
• Еженедельно
• Ежемесячно

🔹 Напоминания:
В настройках можно добавить шаблоны напоминаний (например, "за 1 час", "за 1 день").
Они будут автоматически применяться ко всем новым задачам.
Также можно добавить кастомное напоминание при создании задачи.

По вопросам и предложениям: @your_support"""
    
    await message.answer(help_text)


# ==================== СОЗДАНИЕ ЗАДАЧИ ====================

@router.message(F.text == "➕ Новая задача")
async def start_create_task(message: Message, state: FSMContext):
    """Начало создания задачи"""
    await message.answer("Введи название задачи:")
    await state.set_state(CreateTask.waiting_for_title)


@router.message(CreateTask.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    title = message.text.strip()
    
    if not title:
        await message.answer("❌ Название не может быть пустым. Попробуй еще раз:")
        return
    
    await state.update_data(title=title)
    await message.answer(
        "Введи дату и время (например: завтра 18:00, 06.04.2026 18:00)",
        reply_markup=get_date_quick_buttons()
    )
    await state.set_state(CreateTask.waiting_for_date)


@router.callback_query(CreateTask.waiting_for_date, F.data.startswith("date_"))
async def process_quick_date(callback: CallbackQuery, state: FSMContext):
    """Обработка быстрого выбора даты"""
    date_type = callback.data.replace("date_", "")
    
    user = db.get_user(callback.from_user.id)
    user_tz = pytz.timezone(user['timezone'])
    now = datetime.now(user_tz)
    
    if date_type == "today":
        selected_date = now.date()
    elif date_type == "tomorrow":
        selected_date = (now + timedelta(days=1)).date()
    elif date_type == "week":
        selected_date = (now + timedelta(days=7)).date()
    else:
        await callback.answer("❌ Неизвестный тип даты")
        return
    
    await state.update_data(selected_date=selected_date)
    await callback.message.edit_text("Введи время (например: 18:00):")
    await state.set_state(CreateTask.waiting_for_time)
    await callback.answer()


@router.message(CreateTask.waiting_for_date)
async def process_task_date(message: Message, state: FSMContext):
    """Обработка даты задачи"""
    user = db.get_user(message.from_user.id)
    user_tz = user['timezone']
    
    # Парсим дату
    parsed_date = parse_date(message.text, user_tz)
    
    if not parsed_date:
        await message.answer(
            "❌ Не понял дату. Попробуй еще раз (например: завтра 18:00, 06.04.2026 18:00)",
            reply_markup=get_date_quick_buttons()
        )
        return
    
    await state.update_data(due_date=parsed_date)
    await message.answer(
        "Выбери приоритет:",
        reply_markup=get_priority_keyboard()
    )
    await state.set_state(CreateTask.waiting_for_priority)


@router.message(CreateTask.waiting_for_time)
async def process_task_time(message: Message, state: FSMContext):
    """Обработка времени задачи"""
    time_tuple = parse_time(message.text)
    
    if not time_tuple:
        await message.answer("❌ Не понял время. Попробуй еще раз (например: 18:00):")
        return
    
    hours, minutes = time_tuple
    data = await state.get_data()
    selected_date = data['selected_date']
    
    user = db.get_user(message.from_user.id)
    user_tz = pytz.timezone(user['timezone'])
    
    # Комбинируем дату и время
    due_date = datetime.combine(selected_date, datetime.min.time().replace(hour=hours, minute=minutes))
    due_date = user_tz.localize(due_date)
    
    await state.update_data(due_date=due_date)
    await message.answer(
        "Выбери приоритет:",
        reply_markup=get_priority_keyboard()
    )
    await state.set_state(CreateTask.waiting_for_priority)


@router.callback_query(CreateTask.waiting_for_priority, F.data.startswith("priority_"))
async def process_task_priority(callback: CallbackQuery, state: FSMContext):
    """Обработка приоритета задачи"""
    priority = callback.data.replace("priority_", "")
    await state.update_data(priority=priority)
    
    await callback.message.edit_text(
        "Сделать задачу повторяющейся?",
        reply_markup=get_recurring_keyboard()
    )
    await state.set_state(CreateTask.waiting_for_recurring)
    await callback.answer()


@router.callback_query(CreateTask.waiting_for_recurring, F.data.startswith("recurring_"))
async def process_task_recurring(callback: CallbackQuery, state: FSMContext):
    """Обработка повторения задачи"""
    recurring_type = callback.data.replace("recurring_", "")
    
    if recurring_type == "no":
        await state.update_data(is_recurring=False, recurring_pattern=None)
    else:
        await state.update_data(is_recurring=True, recurring_pattern=recurring_type)
    
    # Сразу создаем задачу (без вопроса о кастомном напоминании)
    await callback.message.edit_text("Создаю задачу...")
    await create_task_final(callback.message, state, callback.from_user.id)
    await callback.answer()


async def create_task_final(message: Message, state: FSMContext, user_id: int):
    """Финальное создание задачи"""
    data = await state.get_data()
    
    title = data['title']
    due_date = data['due_date']
    priority = data['priority']
    is_recurring = data.get('is_recurring', False)
    recurring_pattern = data.get('recurring_pattern')
    
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
        due_date=due_date_utc,
        priority=priority,
        is_recurring=is_recurring,
        recurring_pattern=recurring_pattern
    )
    
    if not task_id:
        await message.answer("❌ Произошла ошибка при создании задачи. Попробуй еще раз.")
        await state.clear()
        return
    
    # Создаем напоминания (7:00, 14:00, 19:00 + момент дедлайна)
    db.create_reminders_from_templates(task_id, user_id, due_date_utc)
    
    # Формируем сообщение
    user = db.get_user(user_id)
    formatted_date = format_date(due_date_utc, user['timezone'])
    priority_emoji = get_priority_emoji(priority)
    
    recurring_text = ""
    if is_recurring:
        recurring_map = {'daily': 'Ежедневно', 'weekly': 'Еженедельно', 'monthly': 'Ежемесячно'}
        recurring_text = f"\n🔁 Повторяется: {recurring_map[recurring_pattern]}"
    
    reminders = db.get_task_reminders(task_id)
    reminders_text = ""
    if reminders:
        reminders_list = [format_date(r['remind_at'], user['timezone']) for r in reminders]
        reminders_text = f"\n🔔 Напоминания: {', '.join(reminders_list)}"
    
    await message.answer(
        f"✅ Задача создана!\n\n"
        f"{priority_emoji} {title}\n"
        f"📅 {formatted_date}"
        f"{recurring_text}"
        f"{reminders_text}",
        reply_markup=get_main_menu()
    )
    
    await state.clear()
    logger.info(f"Task {task_id} created by user {user_id}")


# ==================== ПРОСМОТР ЗАДАЧ ====================

@router.message(F.text == "📋 Мои задачи")
async def show_my_tasks(message: Message, state: FSMContext):
    """Показать все активные задачи"""
    await state.clear()  # Очищаем FSM состояние
    await show_tasks_page(message, message.from_user.id, page=1, is_completed=False)


@router.message(F.text == "📅 Сегодня")
async def show_today_tasks(message: Message, state: FSMContext):
    """Показать задачи на сегодня"""
    await state.clear()  # Очищаем FSM состояние
    user_id = message.from_user.id
    user = db.get_user(user_id)
    user_tz = pytz.timezone(user['timezone'])
    now = datetime.now(user_tz)
    
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    tasks = db.get_today_tasks(user_id, start_of_day, end_of_day)
    
    if not tasks:
        await message.answer("📅 На сегодня задач нет!")
        return
    
    await format_and_send_tasks(message, tasks, user['timezone'], f"📅 Задачи на сегодня ({len(tasks)}):")


@router.message(F.text == "✅ Выполненные")
async def show_completed_tasks(message: Message, state: FSMContext):
    """Показать выполненные задачи"""
    await state.clear()  # Очищаем FSM состояние
    await show_tasks_page(message, message.from_user.id, page=1, is_completed=True)


async def show_tasks_page(message: Message, user_id: int, page: int, is_completed: bool):
    """Показать страницу задач с пагинацией"""
    total_tasks = db.get_tasks_count(user_id, is_completed)
    
    if total_tasks == 0:
        if is_completed:
            await message.answer("✅ Выполненных задач пока нет!")
        else:
            await message.answer("📋 Активных задач пока нет!\n\nСоздай новую задачу через меню.")
        return
    
    total_pages = math.ceil(total_tasks / TASKS_PER_PAGE)
    offset = (page - 1) * TASKS_PER_PAGE
    
    tasks = db.get_user_tasks(user_id, is_completed, limit=TASKS_PER_PAGE, offset=offset)
    
    user = db.get_user(user_id)
    
    if is_completed:
        header = f"✅ Выполненные задачи ({total_tasks}):\n\nСтраница {page} из {total_pages}\n\n"
    else:
        header = f"📋 Мои задачи ({total_tasks}):\n\nСтраница {page} из {total_pages}\n\n"
    
    await format_and_send_tasks(message, tasks, user['timezone'], header, page, total_pages, is_completed)


async def format_and_send_tasks(message: Message, tasks: list, user_tz: str, header: str, 
                                 page: int = None, total_pages: int = None, is_completed: bool = False):
    """Форматирование и отправка списка задач"""
    text = header
    
    for i, task in enumerate(tasks, 1):
        priority_emoji = get_priority_emoji(task['priority'])
        formatted_date = format_date(task['due_date'], user_tz)
        
        if is_completed:
            completed_date = format_date(task['completed_at'], user_tz)
            text += f"{i}. {task['title']}\n   ✅ Выполнено: {completed_date}\n"
        else:
            text += f"{i}. {priority_emoji} {task['title']}\n   📅 {formatted_date}\n"
        
        # Добавляем inline-кнопки для каждой задачи
        if is_completed:
            keyboard = get_completed_task_actions_keyboard(task['id'])
        else:
            keyboard = get_task_actions_keyboard(task['id'])
        
        await message.answer(text, reply_markup=keyboard)
        text = ""
    
    # Добавляем пагинацию если нужно
    if page and total_pages and total_pages > 1:
        prefix = "completed_page" if is_completed else "page"
        pagination_kb = get_pagination_keyboard(page, total_pages, prefix)
        await message.answer("Навигация:", reply_markup=pagination_kb)


@router.callback_query(F.data.startswith("page_"))
async def paginate_tasks(callback: CallbackQuery):
    """Пагинация активных задач"""
    page = int(callback.data.replace("page_", ""))
    await callback.message.delete()
    await show_tasks_page(callback.message, callback.from_user.id, page, is_completed=False)
    await callback.answer()


@router.callback_query(F.data.startswith("completed_page_"))
async def paginate_completed_tasks(callback: CallbackQuery):
    """Пагинация выполненных задач"""
    page = int(callback.data.replace("completed_page_", ""))
    await callback.message.delete()
    await show_tasks_page(callback.message, callback.from_user.id, page, is_completed=True)
    await callback.answer()


# ==================== ДЕЙСТВИЯ С ЗАДАЧАМИ ====================

@router.callback_query(F.data.startswith("complete_"))
async def complete_task(callback: CallbackQuery):
    """Выполнить задачу"""
    task_id = int(callback.data.replace("complete_", ""))
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Помечаем задачу выполненной
    db.complete_task(task_id)
    
    # Удаляем напоминания
    db.delete_task_reminders(task_id)
    
    # Если задача повторяющаяся - создаем новую
    if task['is_recurring']:
        next_date = calculate_next_recurring_date(task['due_date'], task['recurring_pattern'])
        
        new_task_id = db.create_task(
            user_id=task['user_id'],
            title=task['title'],
            due_date=next_date,
            priority=task['priority'],
            is_recurring=True,
            recurring_pattern=task['recurring_pattern']
        )
        
        if new_task_id:
            db.create_reminders_from_templates(new_task_id, task['user_id'], next_date)
            
            user = db.get_user(task['user_id'])
            formatted_next_date = format_date(next_date, user['timezone'])
            
            await callback.message.edit_text(
                f"✅ Задача выполнена!\n\n"
                f"Создана следующая: {formatted_next_date}"
            )
    else:
        await callback.message.edit_text("✅ Задача выполнена!")
    
    await callback.answer()
    logger.info(f"Task {task_id} completed")


@router.callback_query(F.data.startswith("delete_"))
async def ask_delete_confirmation(callback: CallbackQuery):
    """Запрос подтверждения удаления"""
    task_id_str = callback.data.replace("delete_", "").replace("completed_", "")
    task_id = int(task_id_str)
    
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"Удалить задачу \"{task['title']}\"?",
        reply_markup=get_delete_confirmation_keyboard(task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_task(callback: CallbackQuery):
    """Подтверждение удаления задачи"""
    task_id = int(callback.data.replace("confirm_delete_", ""))
    
    success = db.delete_task(task_id)
    
    if success:
        await callback.message.edit_text("🗑️ Задача удалена")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении задачи")
    
    await callback.answer()
    logger.info(f"Task {task_id} deleted")


@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete_task(callback: CallbackQuery):
    """Отмена удаления задачи"""
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.answer()


@router.callback_query(F.data.startswith("restore_"))
async def restore_completed_task(callback: CallbackQuery, state: FSMContext):
    """Восстановление выполненной задачи"""
    task_id = int(callback.data.replace("restore_", ""))
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    user = db.get_user(callback.from_user.id)
    user_tz = pytz.timezone(user['timezone'])
    now = datetime.now(user_tz)
    
    # Проверяем дату задачи (приводим к одному часовому поясу)
    task_due_date = task['due_date'].astimezone(user_tz) if task['due_date'].tzinfo else user_tz.localize(task['due_date'])
    
    if task_due_date < now:
        # Дата в прошлом - спрашиваем новую
        await state.update_data(restore_task_id=task_id)
        await callback.message.edit_text(
            "Дата задачи уже прошла. Введи новую дату и время:"
        )
        await state.set_state(EditTask.editing_date)
    else:
        # Дата в будущем - восстанавливаем
        db.restore_task(task_id)
        db.create_reminders_from_templates(task_id, callback.from_user.id, task['due_date'])
        await callback.message.edit_text("🔄 Задача восстановлена!")
    
    await callback.answer()


# ==================== РЕДАКТИРОВАНИЕ ЗАДАЧИ ====================

@router.callback_query(F.data.startswith("edit_"))
async def show_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования задачи"""
    task_id = int(callback.data.replace("edit_", ""))
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    await state.update_data(editing_task_id=task_id)
    
    user = db.get_user(callback.from_user.id)
    formatted_date = format_date(task['due_date'], user['timezone'])
    priority_emoji = get_priority_emoji(task['priority'])
    
    await callback.message.edit_text(
        f"Редактирование задачи:\n\n"
        f"{priority_emoji} {task['title']}\n"
        f"📅 {formatted_date}\n\n"
        f"Что изменить?",
        reply_markup=get_edit_menu_keyboard(task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def start_edit_title(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование названия"""
    task_id = int(callback.data.replace("edit_title_", ""))
    await state.update_data(editing_task_id=task_id)
    await callback.message.edit_text("Введи новое название задачи:")
    await state.set_state(EditTask.editing_title)
    await callback.answer()


@router.message(EditTask.editing_title)
async def process_edit_title(message: Message, state: FSMContext):
    """Обработка нового названия"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    
    new_title = message.text.strip()
    
    if not new_title:
        await message.answer("❌ Название не может быть пустым. Попробуй еще раз:")
        return
    
    success = db.update_task(task_id, title=new_title)
    
    if success:
        await message.answer("✅ Название обновлено!")
    else:
        await message.answer("❌ Ошибка при обновлении")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_date_"))
async def start_edit_date(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование даты"""
    task_id = int(callback.data.replace("edit_date_", ""))
    await state.update_data(editing_task_id=task_id)
    await callback.message.edit_text(
        "Введи новую дату и время (например: завтра 18:00):",
        reply_markup=get_date_quick_buttons()
    )
    await state.set_state(EditTask.editing_date)
    await callback.answer()


@router.message(EditTask.editing_date)
async def process_edit_date(message: Message, state: FSMContext):
    """Обработка новой даты"""
    data = await state.get_data()
    task_id = data.get('editing_task_id') or data.get('restore_task_id')
    
    user = db.get_user(message.from_user.id)
    user_tz = user['timezone']
    
    parsed_date = parse_date(message.text, user_tz)
    
    if not parsed_date:
        await message.answer("❌ Не понял дату. Попробуй еще раз:")
        return
    
    # Конвертируем в UTC для сохранения в БД
    parsed_date_utc = parsed_date.astimezone(pytz.UTC)
    
    # Обновляем дату задачи
    success = db.update_task(task_id, due_date=parsed_date_utc)
    
    if success:
        # Пересоздаем напоминания
        db.delete_task_reminders(task_id)
        
        # Если это восстановление задачи
        if data.get('restore_task_id'):
            db.restore_task(task_id, parsed_date_utc)
            db.create_reminders_from_templates(task_id, message.from_user.id, parsed_date_utc)
            await message.answer("🔄 Задача восстановлена с новой датой!")
        else:
            db.create_reminders_from_templates(task_id, message.from_user.id, parsed_date_utc)
            await message.answer("✅ Дата обновлена!")
    else:
        await message.answer("❌ Ошибка при обновлении")
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_priority_"))
async def start_edit_priority(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование приоритета"""
    task_id = int(callback.data.replace("edit_priority_", ""))
    await state.update_data(editing_task_id=task_id)
    await callback.message.edit_text(
        "Выбери новый приоритет:",
        reply_markup=get_priority_keyboard()
    )
    await state.set_state(EditTask.editing_priority)
    await callback.answer()


@router.callback_query(EditTask.editing_priority, F.data.startswith("priority_"))
async def process_edit_priority(callback: CallbackQuery, state: FSMContext):
    """Обработка нового приоритета"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    
    priority = callback.data.replace("priority_", "")
    success = db.update_task(task_id, priority=priority)
    
    if success:
        await callback.message.edit_text("✅ Приоритет обновлен!")
    else:
        await callback.message.edit_text("❌ Ошибка при обновлении")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("edit_recurring_"))
async def start_edit_recurring(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование повторения"""
    task_id = int(callback.data.replace("edit_recurring_", ""))
    await state.update_data(editing_task_id=task_id)
    await callback.message.edit_text(
        "Выбери новый режим повторения:",
        reply_markup=get_recurring_keyboard()
    )
    await state.set_state(EditTask.editing_recurring)
    await callback.answer()


@router.callback_query(EditTask.editing_recurring, F.data.startswith("recurring_"))
async def process_edit_recurring(callback: CallbackQuery, state: FSMContext):
    """Обработка нового режима повторения"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    
    recurring_type = callback.data.replace("recurring_", "")
    
    if recurring_type == "no":
        success = db.update_task(task_id, is_recurring=False, recurring_pattern=None)
    else:
        success = db.update_task(task_id, is_recurring=True, recurring_pattern=recurring_type)
    
    if success:
        await callback.message.edit_text("✅ Режим повторения обновлен!")
    else:
        await callback.message.edit_text("❌ Ошибка при обновлении")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("edit_reminders_"))
async def show_reminders_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования напоминаний"""
    task_id = int(callback.data.replace("edit_reminders_", ""))
    await state.update_data(editing_task_id=task_id)
    
    reminders = db.get_task_reminders(task_id)
    user = db.get_user(callback.from_user.id)
    
    if reminders:
        reminders_text = "Текущие напоминания:\n"
        for i, reminder in enumerate(reminders, 1):
            formatted = format_date(reminder['remind_at'], user['timezone'])
            reminders_text += f"{i}. {formatted}\n"
    else:
        reminders_text = "Напоминаний пока нет.\n"
    
    await callback.message.edit_text(
        reminders_text,
        reply_markup=get_reminder_actions_keyboard(task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_reminder_"))
async def start_add_reminder(callback: CallbackQuery, state: FSMContext):
    """Начать добавление напоминания"""
    task_id = int(callback.data.replace("add_reminder_", ""))
    await state.update_data(editing_task_id=task_id)
    await callback.message.edit_text("Введи время напоминания (например: за 2 часа, за 3 дня):")
    await state.set_state(EditTask.adding_reminder)
    await callback.answer()


@router.message(EditTask.adding_reminder)
async def process_add_reminder(message: Message, state: FSMContext):
    """Обработка добавления напоминания"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    
    reminder_offset = parse_reminder_offset(message.text)
    
    if not reminder_offset:
        await message.answer("❌ Не понял время. Попробуй еще раз:")
        return
    
    task = db.get_task(task_id)
    offset_type = reminder_offset['offset_type']
    offset_value = reminder_offset['offset_value']
    
    if offset_type == 'hours':
        remind_at = task['due_date'] - timedelta(hours=offset_value)
    else:
        remind_at = task['due_date'] - timedelta(days=offset_value)
    
    if remind_at > datetime.now(pytz.UTC):
        db.create_reminder(task_id, remind_at)
        await message.answer("✅ Напоминание добавлено!")
    else:
        await message.answer("❌ Время напоминания уже прошло")
    
    await state.clear()


@router.callback_query(F.data.startswith("back_to_edit_"))
async def back_to_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в меню редактирования"""
    task_id = int(callback.data.replace("back_to_edit_", ""))
    await show_edit_menu(callback, state)


@router.callback_query(F.data.startswith("back_to_task_"))
async def back_to_task_view(callback: CallbackQuery):
    """Вернуться к просмотру задачи"""
    await callback.message.edit_text("◀️ Возврат к задаче")
    await callback.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_task_details(callback: CallbackQuery):
    """Просмотр деталей задачи"""
    task_id = int(callback.data.replace("view_", ""))
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    user = db.get_user(callback.from_user.id)
    formatted_date = format_date(task['due_date'], user['timezone'])
    priority_emoji = get_priority_emoji(task['priority'])
    
    text = f"{priority_emoji} {task['title']}\n📅 {formatted_date}"
    
    if task['is_recurring']:
        recurring_map = {'daily': 'Ежедневно', 'weekly': 'Еженедельно', 'monthly': 'Ежемесячно'}
        text += f"\n🔁 {recurring_map[task['recurring_pattern']]}"
    
    await callback.message.edit_text(text, reply_markup=get_task_actions_keyboard(task_id))
    await callback.answer()


# ==================== НАСТРОЙКИ ====================

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, state: FSMContext):
    """Показать настройки"""
    await state.clear()  # Очищаем FSM состояние
    user_id = message.from_user.id
    user = db.get_user(user_id)
    templates = db.get_user_reminder_templates(user_id)
    
    tz_name = get_timezone_name(user['timezone'])
    
    text = "⚙️ Настройки\n\n"
    text += "🔔 Шаблоны напоминаний:\n"
    
    if templates:
        for i, template in enumerate(templates, 1):
            text += f"{i}. {format_reminder_template(template)} ✅\n"
    else:
        text += "Нет активных шаблонов\n"
    
    text += f"\n🌍 Часовой пояс: {tz_name}"
    
    await message.answer(text, reply_markup=get_settings_keyboard())


@router.callback_query(F.data == "settings_add_template")
async def start_add_template(callback: CallbackQuery, state: FSMContext):
    """Начать добавление шаблона"""
    await callback.message.edit_text("Введи час напоминания (например: 7, 14, 19, 22):")
    await state.set_state(Settings.adding_template)
    await callback.answer()


@router.message(Settings.adding_template)
async def process_add_template(message: Message, state: FSMContext):
    """Обработка добавления шаблона"""
    try:
        hour = int(message.text.strip())
        if hour < 0 or hour > 23:
            await message.answer("❌ Час должен быть от 0 до 23. Попробуй еще раз:")
            return
    except ValueError:
        await message.answer("❌ Введи число от 0 до 23 (например: 7, 14, 19):")
        return
    
    template_id = db.create_reminder_template(message.from_user.id, hour)
    
    if template_id:
        await message.answer(f"✅ Напоминание на {hour:02d}:00 добавлено!")
    else:
        await message.answer("❌ Ошибка при добавлении напоминания")
    
    await state.clear()


@router.callback_query(F.data == "settings_delete_template")
async def start_delete_template(callback: CallbackQuery):
    """Начать удаление шаблона"""
    user_id = callback.from_user.id
    templates = db.get_user_reminder_templates(user_id)
    
    if not templates:
        await callback.answer("❌ Нет шаблонов для удаления", show_alert=True)
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    
    for template in templates:
        text = f"🗑️ {format_reminder_template(template)}"
        kb.button(text=text, callback_data=f"delete_template_{template['id']}")
    
    kb.button(text="◀️ Назад", callback_data="settings_back")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "Выбери шаблон для удаления:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_template_"))
async def confirm_delete_template(callback: CallbackQuery):
    """Удаление шаблона"""
    template_id = int(callback.data.replace("delete_template_", ""))
    
    success = db.delete_reminder_template(template_id)
    
    if success:
        await callback.message.edit_text("🗑️ Шаблон удален")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении")
    
    await callback.answer()


@router.callback_query(F.data == "settings_change_timezone")
async def start_change_timezone(callback: CallbackQuery, state: FSMContext):
    """Начать изменение часового пояса"""
    await callback.message.edit_text(
        "Выбери новый часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )
    await state.set_state(Settings.changing_timezone)
    await callback.answer()


@router.callback_query(Settings.changing_timezone, F.data.startswith("tz_"))
async def process_timezone_change(callback: CallbackQuery, state: FSMContext):
    """Обработка изменения часового пояса"""
    timezone = callback.data.replace("tz_", "")
    
    success = db.update_user_timezone(callback.from_user.id, timezone)
    
    if success:
        tz_name = get_timezone_name(timezone)
        await callback.message.edit_text(f"✅ Часовой пояс изменен на {tz_name}")
    else:
        await callback.message.edit_text("❌ Ошибка при изменении часового пояса")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "settings_back")
async def back_to_settings(callback: CallbackQuery):
    """Вернуться в настройки"""
    await callback.message.delete()
    # Создаем новое сообщение с настройками
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    templates = db.get_user_reminder_templates(user_id)
    
    tz_name = get_timezone_name(user['timezone'])
    
    text = "⚙️ Настройки\n\n"
    text += "🔔 Шаблоны напоминаний:\n"
    
    if templates:
        for i, template in enumerate(templates, 1):
            text += f"{i}. {format_reminder_template(template)} ✅\n"
    else:
        text += "Нет активных шаблонов\n"
    
    text += f"\n🌍 Часовой пояс: {tz_name}"
    
    await callback.message.answer(text, reply_markup=get_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()
