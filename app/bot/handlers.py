import asyncio
import logging
import json
from pathlib import Path
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.storage import load_homeworks, save_homeworks
from app.database.db import (
    is_subscribed,
    add_subscription,
    remove_subscription,
    get_user_subgroup,
    set_user_subgroup,
    get_all_user_ids,
)
from app.bot.keyboards import (
    get_notification_keyboard,
    get_subgroup_keyboard,
    get_sheet_link_keyboard,
    get_report_confirm_keyboard,
    get_schedule_link_keyboard,
    get_main_menu_keyboard,
)
from app.utils.notifications import (
    format_homeworks,
    send_safe,
    message_entities_to_html,
)
from app.parser.google_sheets import parse_homework
from app.parser.hse_schedule import get_today_schedule_message
from app.config import ADMIN_TG

# === FAQ storage ===
FAQ_FILE = Path("data/faq.json")

def load_faq():
    FAQ_FILE.parent.mkdir(exist_ok=True)
    if not FAQ_FILE.exists():
        return []
    try:
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("faq", [])
    except (json.JSONDecodeError, IOError):
        return []

def save_faq(faq_list):
    FAQ_FILE.parent.mkdir(exist_ok=True)
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump({"faq": faq_list}, f, ensure_ascii=False, indent=2)

# === Router ===
router = Router()
logger = logging.getLogger(__name__)

class ReportStates(StatesGroup):
    wait_message = State()
    wait_confirm = State()

# === COMMANDS ===

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    subgroup = await get_user_subgroup(user_id)

    if subgroup:
        # Если подгруппа уже выбрана — показываем главное меню с приветствием
        text = (
            f"🌟 Привет, {message.from_user.first_name}!\n\n"
            f"👥 Твоя подгруппа: *{subgroup}*\n\n"
            "📋 *Доступные команды:*\n"
            "   /info — показать ДЗ на 2 недели\n"
            "   /schedule — расписание на сегодня\n"
            "   /faq — поиск по базе знаний\n"
            "   /notification — управление подпиской\n"
            "   /menu — главное меню\n"
            "   /help — помощь"
        )
        keyboard = get_main_menu_keyboard()
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Если подгруппа не выбрана — предлагаем выбрать, но с твоим стилем
        text = (
            f"🌟 Привет, {message.from_user.first_name}!\n\n"
            "Я — ВышАссистент, твой помощник в адаптации к ВШЭ.\n\n"
            "Чтобы я мог показывать тебе расписание и домашние задания, "
            "выбери свою подгруппу:"
        )
        keyboard = get_subgroup_keyboard()
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    keyboard = get_main_menu_keyboard()
    await message.answer(
        "*Главное меню*\n\n"
        "Выберите нужный раздел или напишите свой вопрос — я попробую найти ответ.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Напишите вопрос после команды, например:\n"
            "/faq что делать если заболел"
        )
        return

    query = args[1].lower()
    faq_list = load_faq()

    results = []
    for entry in faq_list:
        if query in entry.get("keywords", "").lower() or query in entry.get("question", "").lower():
            results.append(entry)

    if not results:
        await message.answer(
            "Я не нашёл ответа на твой вопрос.\n\n"
            "Попробуй переформулировать или обратись в учебный офис."
        )
        return

    entry = results[0]
    await message.answer(
        f"*{entry['question']}*\n\n{entry['answer']}",
        parse_mode="Markdown"
    )


@router.message(Command("add_faq"))
async def cmd_add_faq(message: Message):
    if message.from_user.id != ADMIN_TG:
        await message.answer("Доступ запрещён")
        return

    import re
    parts = re.findall(r'"([^"]*)"', message.text)
    if len(parts) < 3:
        await message.answer("Используйте: /add_faq \"Вопрос\" \"Ответ\" \"ключевые, слова\"")
        return

    question, answer, keywords = parts[0], parts[1], parts[2]
    faq_list = load_faq()
    faq_list.append({"question": question, "answer": answer, "keywords": keywords})
    save_faq(faq_list)
    await message.answer("✅ Запись добавлена в FAQ")


@router.message(Command("info"))
async def cmd_info(message: Message):
    subgroup = await get_user_subgroup(message.from_user.id)
    if not subgroup:
        await message.answer("⚠️ Сначала выберите подгруппу командой /start", reply_markup=get_subgroup_keyboard())
        return

    homeworks = load_homeworks()
    if not homeworks:
        await message.answer("⏳ Загружаю данные из таблицы...")
        try:
            homeworks = await parse_homework()
            if homeworks:
                save_homeworks(homeworks)
        except Exception:
            await message.answer("❌ Не удалось загрузить данные. Попробуйте позже.")
            return

    filtered = [h for h in homeworks if h.subgroup == subgroup or h.subgroup == "Все"]
    if not filtered:
        await message.answer(f"📭 ДЗ для <b>{subgroup}</b> на ближайшие 2 недели не найдено.")
        return

    messages = format_homeworks(filtered, subgroup=subgroup)
    keyboard = get_sheet_link_keyboard()
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            await message.answer(msg, reply_markup=keyboard)
        else:
            await message.answer(msg)


@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    subgroup = await get_user_subgroup(message.from_user.id)
    if not subgroup:
        await message.answer("⚠️ Сначала выберите подгруппу командой /start", reply_markup=get_subgroup_keyboard())
        return

    await message.answer("⏳ Загружаю расписание на сегодня...")
    try:
        text = await get_today_schedule_message(subgroup=subgroup)
        await message.answer(text, disable_web_page_preview=True, reply_markup=get_schedule_link_keyboard())
    except Exception:
        await message.answer("❌ Не удалось загрузить расписание. Попробуйте позже.")


@router.message(Command("notification"))
async def cmd_notification(message: Message):
    subgroup = await get_user_subgroup(message.from_user.id)
    if not subgroup:
        await message.answer("⚠️ Сначала выберите подгруппу командой /start", reply_markup=get_subgroup_keyboard())
        return

    subscribed = await is_subscribed(message.from_user.id)
    text = "🔔 Вы подписаны на уведомления." if subscribed else "🔕 Вы не подписаны."
    keyboard = get_notification_keyboard(subscribed)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📋 *Доступные команды:*\n\n"
        "   /start — выбор подгруппы\n"
        "   /menu — главное меню\n"
        "   /info — ДЗ на 2 недели\n"
        "   /schedule — расписание на сегодня\n"
        "   /faq — поиск по базе знаний\n"
        "   /notification — подписка\n"
        "   /help — это сообщение"
    )
    await message.answer(text, parse_mode="Markdown")



@router.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery):
    if callback.data == "menu_schedule":
        await cmd_schedule(callback.message)
    elif callback.data == "menu_homework":
        await cmd_info(callback.message)
    elif callback.data == "menu_faq":
        await callback.message.answer("❓ Напишите /faq и ваш вопрос, например:\n/faq что делать если заболел")
    elif callback.data == "menu_notification":
        await cmd_notification(callback.message)
    elif callback.data == "menu_help":
        await cmd_help(callback.message)
    await callback.answer()


# === Обработка callback-запросов ===

@router.callback_query(lambda c: c.data in ["subscribe", "unsubscribe"])
async def handle_subscription(callback: CallbackQuery):
    subgroup = await get_user_subgroup(callback.from_user.id)
    if not subgroup:
        await callback.answer("⚠️ Сначала выберите подгруппу командой /start", show_alert=True)
        return

    if callback.data == "subscribe":
        await add_subscription(callback.from_user.id)
        text = "✅ Вы подписались на уведомления."
        subscribed = True
    else:
        await remove_subscription(callback.from_user.id)
        text = "❌ Вы отписались от уведомлений."
        subscribed = False

    await callback.message.edit_text(text, reply_markup=get_notification_keyboard(subscribed))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("subgroup:"))
async def handle_subgroup(callback: CallbackQuery):
    subgroup = callback.data.split(":", 1)[1]
    await set_user_subgroup(callback.from_user.id, subgroup)

    text = (
        f"✅ Подгруппа <b>{subgroup}</b> сохранена!\n\n"
        "📋 Доступные команды:\n"
        "   /info — показать ДЗ\n"
        "   /schedule — расписание\n"
        "   /faq — поиск по FAQ\n"
        "   /notification — подписка"
    )
    keyboard = get_main_menu_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(f"Выбрана подгруппа {subgroup}")

# === Report commands ===

@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TG:
        return
    await state.set_state(ReportStates.wait_message)
    await state.update_data(report_test=False)
    await message.answer("Отправьте сообщение для рассылки:")


@router.message(Command("test_report"))
async def cmd_test_report(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TG:
        return
    await state.set_state(ReportStates.wait_message)
    await state.update_data(report_test=True)
    await message.answer("Отправьте сообщение (тест — получите только вы):")


@router.message(StateFilter(ReportStates.wait_message))
async def report_receive_message(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_TG:
        return
    if not message.text:
        await message.answer("Отправьте текстовое сообщение.")
        return
    report_html = message_entities_to_html(message.text, message.entities)
    await state.update_data(report_text=report_html)
    await state.set_state(ReportStates.wait_confirm)
    await message.answer(report_html, reply_markup=get_report_confirm_keyboard())


@router.callback_query(StateFilter(ReportStates.wait_confirm), lambda c: c.data in ["report_yes", "report_no"])
async def report_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_TG:
        await callback.answer()
        return
    if callback.data == "report_no":
        await callback.message.delete()
        await state.clear()
        await callback.answer("Отменено")
        return
    data = await state.get_data()
    text = data.get("report_text", "")
    await state.clear()
    if not text:
        await callback.answer("Нет текста", show_alert=True)
        return
    user_ids = [ADMIN_TG] if data.get("report_test") else await get_all_user_ids()
    sent = 0
    for uid in user_ids:
        if await send_safe(callback.bot, uid, text):
            sent += 1
        await asyncio.sleep(0.05)
    try:
        await callback.message.edit_text(text + f"\n\n✅ Разослано {sent} из {len(user_ids)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    except Exception:
        pass
    await callback.answer("Готово")