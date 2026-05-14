import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)


TOKEN = ""

# Создаём бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌟 Привет, первокурсник!\n\n"
        "Я — ВышАссистент, твой помощник в адаптации к ВШЭ.\n\n"
        "Вот что я умею:\n"
        "• 📅 Показывать дедлайны\n"
        "• 🔍 Отвечать на вопросы\n"
        "• 🔔 Напоминать о важном\n\n"
        "Нажми /menu, чтобы начать."
    )


# Обработчик команды /menu
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer(
        "📋 Главное меню:\n\n"
        "🎓 Учебный процесс\n"
        "📅 Дедлайны и ДЗ\n"
        "🩺 Если заболел\n"
        "📞 К кому обратиться?\n"
        "🔔 Настроить напоминания\n\n"
        "Напиши свой вопрос текстом — я попробую найти ответ."
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
