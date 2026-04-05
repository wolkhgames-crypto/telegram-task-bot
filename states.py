from aiogram.fsm.state import State, StatesGroup


class Setup(StatesGroup):
    """Состояния для первоначальной настройки пользователя"""
    waiting_for_timezone = State()


class CreateTask(StatesGroup):
    """Состояния для создания задачи"""
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_priority = State()
    waiting_for_recurring = State()
    waiting_for_custom_reminder = State()


class EditTask(StatesGroup):
    """Состояния для редактирования задачи"""
    choosing_field = State()
    editing_title = State()
    editing_date = State()
    editing_time = State()
    editing_priority = State()
    editing_recurring = State()
    editing_reminders = State()
    adding_reminder = State()
    deleting_reminder = State()


class Settings(StatesGroup):
    """Состояния для настроек"""
    main_menu = State()
    adding_template = State()
    deleting_template = State()
    changing_timezone = State()
