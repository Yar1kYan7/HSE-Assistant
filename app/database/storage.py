import json
from datetime import date
from pathlib import Path
from typing import List
from app.parser.models import Homework


STORAGE_FILE = Path("data/storage.json")


def load_homeworks() -> List[Homework]:
    STORAGE_FILE.parent.mkdir(exist_ok=True)
    
    if not STORAGE_FILE.exists():
        return []
    
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []
    
    result = []
    for item in data.get("homeworks", []):
        try:
            result.append(Homework(
                subject=item["subject"],
                date=date.fromisoformat(item["date"]),
                subgroup=item["subgroup"],
                content=item["content"],
                link=item.get("link"),
            ))
        except (KeyError, ValueError):
            continue
    
    return result


def save_homeworks(homeworks: List[Homework]):
    STORAGE_FILE.parent.mkdir(exist_ok=True)
    
    data = {"homeworks": [
        {
            "subject": h.subject,
            "date": h.date.isoformat(),
            "subgroup": h.subgroup,
            "content": h.content,
            **({"link": h.link} if h.link else {}),
        }
        for h in homeworks
    ]}
    
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


from pathlib import Path

FAQ_FILE = Path("data/faq.json")

def load_faq() -> List[dict]:
    """Загружает FAQ из JSON-файла."""
    if not FAQ_FILE.exists():
        return []
    try:
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("faq", [])
    except (json.JSONDecodeError, IOError):
        return []

def save_faq(faq_list: List[dict]):
    """Сохраняет FAQ в JSON-файл."""
    FAQ_FILE.parent.mkdir(exist_ok=True)
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump({"faq": faq_list}, f, ensure_ascii=False, indent=2)


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    """Поиск по базе знаний (FAQ)."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❓ Напишите вопрос после команды, например:\n"
            "/faq что делать если заболел"
        )
        return

    query = args[1].lower()
    faq_list = load_faq()

    # Простой поиск по ключевым словам
    results = []
    for entry in faq_list:
        if query in entry.get("keywords", "").lower() or query in entry.get("question", "").lower():
            results.append(entry)

    if not results:
        await message.answer(
            "🤔 Я не нашёл ответа на твой вопрос.\n\n"
            "Попробуй переформулировать или обратись в учебный офис."
        )
        return

    # Показываем первый результат
    entry = results[0]
    await message.answer(
        f"❓ *{entry['question']}*\n\n{entry['answer']}",
        parse_mode="Markdown"
    )