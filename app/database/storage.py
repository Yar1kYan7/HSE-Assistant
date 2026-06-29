from typing import List
import json
from datetime import date
from pathlib import Path
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