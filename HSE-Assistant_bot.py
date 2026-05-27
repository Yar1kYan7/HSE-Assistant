import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Берём токен из переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")


# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Создаём бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Главная клавиатура (ReplyKeyboardMarkup)
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎓 Учебный процесс")],
        [KeyboardButton(text="📅 Дедлайны и ДЗ")],
        [KeyboardButton(text="🩺 Если заболел")],
        [KeyboardButton(text="📞 К кому обратиться?")],
        [KeyboardButton(text="🔔 Настроить напоминания")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,  # автоматически подгонять размер кнопок
    input_field_placeholder="Выберите пункт меню или напишите вопрос..."
)

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌟 Привет, первокурсник!\n\n"
        "Я — ВышАссистент, твой помощник в адаптации к ВШЭ.\n\n"
        "Нажми /menu, чтобы увидеть доступные команды.",
        reply_markup=types.ReplyKeyboardRemove()  # убираем старую клавиатуру (если была)
    )

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer(
        "📋 *Главное меню*\n\n"
        "Выберите нужный раздел или просто напишите свой вопрос — "
        "я попробую найти ответ.",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ КЛАВИАТУРЫ ---

@dp.message(lambda message: message.text == "🎓 Учебный процесс")
async def handle_academic(message: types.Message):
    await message.answer(
        "🎓 *Учебный процесс*\n\n"
        "Выберите интересующий раздел:\n"
        "• Расписание занятий\n"
        "• Система оценивания\n"
        "• Порядок сдачи сессии\n\n"
        "А пока я могу подсказать:\n"
        "👉 Расписание можно найти на сайте программы\n"
        "👉 Система оценивания описана в рабочем ПУДе",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "📅 Дедлайны и ДЗ")
async def handle_deadlines(message: types.Message):
    await message.answer(
        "📅 *Дедлайны и домашние задания*\n\n"
        "Тут я буду показывать список всех дедлайнов.\n"
        "Пока что вот пример:\n\n"
        "🔹 *15.05* — Сдача ДЗ по Python (до 23:59)\n"
        "🔹 *17.05* — Контрольная работа по БД (до 18:00)\n\n"
        "Скоро появится возможность подписаться на напоминания!",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "🩺 Если заболел")
async def handle_sick(message: types.Message):
    await message.answer(
        "🩺 *Если вы заболели*\n\n"
        "1. Сообщите преподавателю в чат до начала пары\n"
        "2. Сообщите в учебный офис\n"
        "3. После выздоровления принесите справку (в течение 3 дней)\n\n"
        "📞 *Контакты учебного офиса:* @hse_perm_office",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "📞 К кому обратиться?")
async def handle_contacts(message: types.Message):
    await message.answer(
        "📞 *К кому обратиться?*\n\n"
        "👩‍🏫 *Учебный офис* — вопросы по документам, справкам, дедлайнам\n"
        "👨‍🏫 *Преподаватели* — вопросы по предметам, ДЗ, консультации\n"
        "👥 *Старосты* — организационные вопросы группы\n"
        "🎓 *Координаторы* — учебный процесс, выбор дисциплин\n\n"
        "👉 Контакты уточняйте в чатах вашей программы.",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "🔔 Настроить напоминания")
async def handle_notify(message: types.Message):
    await message.answer(
        "🔔 *Настройка напоминаний*\n\n"
        "Скоро здесь появится возможность настроить время "
        "и получать ежедневные уведомления о дедлайнах.\n\n"
        "Пока что просто следите за /deadlines!",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "❓ Помощь")
async def handle_help(message: types.Message):
    await message.answer(
        "❓ *Помощь*\n\n"
        "Я умею отвечать на вопросы о:\n"
        "• расписании\n"
        "• дедлайнах\n"
        "• действиях при болезни\n"
        "• контактах\n\n"
        "Просто напиши свой вопрос текстом — я попробую найти ответ.\n\n"
        "Также ты можешь пользоваться кнопками меню.\n\n"
        "Если я не справился — обратись в учебный офис: @hse_perm_office",
        parse_mode="Markdown"
    )




# Обработчик обычных текстовых сообщений
@dp.message()
async def handle_text(message: types.Message):
    text = message.text.lower()

    # Простейший поиск по ключевым словам
    if "заболел" in text or "болезнь" in text or "справка" in text:
        await message.answer(
            "🩺 Если вы заболели:\n\n"
            "1. Сообщите преподавателю в чат до начала пары\n"
            "2. Сообщите в учебный офис\n"
            "3. После выздоровления принесите справку (в течение 3 дней)\n\n"
            "📞 Учебный офис: @hse_perm_office"
        )
    elif "дедлайн" in text or "сдать" in text or "дз" in text:
        await message.answer(
            "📋 Ближайшие дедлайны:\n\n"
            "🔹 15.05 (до 23:59) — Сдача ДЗ по Python\n"
            "🔹 17.05 (до 18:00) — Контрольная работа по БД\n"
            "🔹 20.05 — Выбор тем курсовых\n\n"
            "Для подписки на напоминания нажмите /notify"
        )
    else:
        await message.answer(
            "🤔 Я не нашёл ответ на твой вопрос.\n\n"
            "Попробуй:\n"
            "• переформулировать вопрос\n"
            "• воспользоваться меню (/menu)\n"
            "• обратиться в учебный офис: @hse_perm_office"
        )


# Запуск бота
async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
