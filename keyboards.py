from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Новая задача")
    kb.button(text="📋 Мои задачи")
    kb.button(text="📅 Сегодня")
    kb.button(text="✅ Выполненные")
    kb.button(text="⚙️ Настройки")
    kb.button(text="❓ Помощь")
    kb.adjust(2, 2, 2)
    return kb.as_markup(resize_keyboard=True)


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса геолокации"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📍 Поделиться геолокацией", request_location=True)
    kb.button(text="✏️ Ввести вручную")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с популярными часовыми поясами"""
    kb = InlineKeyboardBuilder()
    timezones = [
        ("🕐 Москва (UTC+3)", "tz_Europe/Moscow"),
        ("🕑 Екатеринбург (UTC+5)", "tz_Asia/Yekaterinburg"),
        ("🕒 Новосибирск (UTC+7)", "tz_Asia/Novosibirsk"),
        ("🕓 Иркутск (UTC+8)", "tz_Asia/Irkutsk"),
        ("🕔 Владивосток (UTC+10)", "tz_Asia/Vladivostok"),
        ("🕕 Камчатка (UTC+12)", "tz_Asia/Kamchatka"),
    ]
    
    for text, callback_data in timezones:
        kb.button(text=text, callback_data=callback_data)
    
    kb.adjust(1)
    return kb.as_markup()


def get_date_quick_buttons() -> InlineKeyboardMarkup:
    """Быстрые кнопки для выбора даты"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Сегодня", callback_data="date_today")
    kb.button(text="Завтра", callback_data="date_tomorrow")
    kb.button(text="Через неделю", callback_data="date_week")
    kb.adjust(3)
    return kb.as_markup()


def get_priority_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора приоритета"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 Высокий", callback_data="priority_high")
    kb.button(text="🟡 Средний", callback_data="priority_medium")
    kb.button(text="🟢 Низкий", callback_data="priority_low")
    kb.adjust(3)
    return kb.as_markup()


def get_recurring_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора повторения"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Ежедневно", callback_data="recurring_daily")
    kb.button(text="📆 Еженедельно", callback_data="recurring_weekly")
    kb.button(text="📊 Ежемесячно", callback_data="recurring_monthly")
    kb.button(text="❌ Нет", callback_data="recurring_no")
    kb.adjust(2, 2)
    return kb.as_markup()


def get_custom_reminder_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для добавления кастомного напоминания"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data="custom_reminder_yes")
    kb.button(text="❌ Нет", callback_data="custom_reminder_no")
    kb.adjust(2)
    return kb.as_markup()


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с задачей"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅", callback_data=f"complete_{task_id}")
    kb.button(text="✏️", callback_data=f"edit_{task_id}")
    kb.button(text="🗑️", callback_data=f"delete_{task_id}")
    kb.adjust(3)
    return kb.as_markup()


def get_pagination_keyboard(current_page: int, total_pages: int, prefix: str = "page") -> InlineKeyboardMarkup:
    """Клавиатура пагинации"""
    kb = InlineKeyboardBuilder()
    
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ Предыдущая", callback_data=f"{prefix}_{current_page - 1}"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️ Следующая", callback_data=f"{prefix}_{current_page + 1}"))
    
    if buttons:
        kb.row(*buttons)
    
    return kb.as_markup()


def get_delete_confirmation_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"confirm_delete_{task_id}")
    kb.button(text="❌ Отмена", callback_data=f"cancel_delete_{task_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_edit_menu_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования задачи"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Название", callback_data=f"edit_title_{task_id}")
    kb.button(text="📅 Дату и время", callback_data=f"edit_date_{task_id}")
    kb.button(text="🎯 Приоритет", callback_data=f"edit_priority_{task_id}")
    kb.button(text="🔁 Повторение", callback_data=f"edit_recurring_{task_id}")
    kb.button(text="🔔 Напоминания", callback_data=f"edit_reminders_{task_id}")
    kb.button(text="◀️ Назад", callback_data=f"back_to_task_{task_id}")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def get_completed_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с выполненной задачей"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Восстановить", callback_data=f"restore_{task_id}")
    kb.button(text="🗑️ Удалить", callback_data=f"delete_completed_{task_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить шаблон", callback_data="settings_add_template")
    kb.button(text="🗑️ Удалить шаблон", callback_data="settings_delete_template")
    kb.button(text="🌍 Изменить часовой пояс", callback_data="settings_change_timezone")
    kb.button(text="◀️ Назад", callback_data="settings_back")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def get_reminder_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с напоминаниями"""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data=f"add_reminder_{task_id}")
    kb.button(text="🗑️ Удалить", callback_data=f"delete_reminder_{task_id}")
    kb.button(text="◀️ Назад", callback_data=f"back_to_edit_{task_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню"""
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ В меню", callback_data="back_to_menu")
    return kb.as_markup()


def get_timezone_confirmation_keyboard(timezone: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения часового пояса"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data=f"confirm_tz_{timezone}")
    kb.button(text="❌ Нет, изменить", callback_data="change_tz")
    kb.adjust(2)
    return kb.as_markup()


def get_reminder_notification_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для уведомления о напоминании"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнить", callback_data=f"complete_{task_id}")
    kb.button(text="👁️ Посмотреть", callback_data=f"view_{task_id}")
    kb.adjust(2)
    return kb.as_markup()
