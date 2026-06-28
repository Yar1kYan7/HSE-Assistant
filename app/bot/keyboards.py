from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import GOOGLE_SHEETS_URL

SCHEDULE_TABLE_URL = "https://perm.hse.ru/students/timetable/"


def get_sheet_link_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📲", url=GOOGLE_SHEETS_URL)]]
    )


def get_schedule_link_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔗", url=SCHEDULE_TABLE_URL)]]
    )


def get_notification_keyboard(is_subscribed: bool) -> InlineKeyboardMarkup:
    if is_subscribed:
        button = InlineKeyboardButton(text="🔔 Отписаться", callback_data="unsubscribe")
    else:
        button = InlineKeyboardButton(text="🔔 Подписаться", callback_data="subscribe")

    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def get_report_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅", callback_data="report_yes"),
                InlineKeyboardButton(text="❌", callback_data="report_no"),
            ]
        ]
    )


def get_subgroup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="ПСАПР-25-1", callback_data="subgroup:ПСАПР-25-1"
                ),
                InlineKeyboardButton(
                    text="ПСАПР-25-2", callback_data="subgroup:ПСАПР-25-2"
                ),
            ]
        ]
    )


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Расписание", callback_data="menu_schedule"),
             InlineKeyboardButton(text="📚 ДЗ", callback_data="menu_homework")],
            [InlineKeyboardButton(text="❓ FAQ / Поиск", callback_data="menu_faq"),
             InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu_notification")],
            [InlineKeyboardButton(text="🆘 Помощь", callback_data="menu_help")]
        ]
    )