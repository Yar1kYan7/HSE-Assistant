import csv
import io
import re
from datetime import date, timedelta, datetime
from typing import List, Dict, Tuple
import httpx
from bs4 import BeautifulSoup

from app.parser.models import Homework
from app.config import GOOGLE_SHEETS_URL


def _extract_sheet_id_and_gid(url: str) -> Tuple[str, str]:
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not match:
        raise ValueError("Не удалось извлечь ID таблицы из URL")
    sheet_id = match.group(1)
    gid_match = re.search(r'gid=(\d+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    return sheet_id, gid


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/csv,text/html,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
}


async def fetch_sheet_html() -> str | None:
    sheet_id, gid = _extract_sheet_id_and_gid(GOOGLE_SHEETS_URL)
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=html&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=html&gid={gid}",
    ]
    try:
        async with httpx.AsyncClient() as client:
            for url in urls:
                response = await client.get(
                    url,
                    headers=DEFAULT_HEADERS,
                    timeout=30.0,
                    follow_redirects=True
                )
                if response.status_code == 200:
                    return response.text
    except httpx.HTTPError:
        pass
    return None


async def fetch_sheet_csv() -> str:
    sheet_id, gid = _extract_sheet_id_and_gid(GOOGLE_SHEETS_URL)
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}",
    ]
    async with httpx.AsyncClient() as client:
        for url in urls:
            response = await client.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 200:
                return response.text
            if response.status_code != 400:
                response.raise_for_status()
    raise httpx.HTTPStatusError(
        "400: ни /export, ни /pub не сработали. Проверьте: 1) Доступ по ссылке = «Просмотр для всех»; 2) или Файл → Опубликовать в интернете.",
        request=response.request,
        response=response,
    )


def _parse_date(date_str: str) -> date | None:
    if not date_str or not (s := date_str.strip()):
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_cell_link(cell) -> Tuple[str, str | None]:
    a = cell.find("a", href=True)
    if a:
        href = (a.get("href") or "").strip()
        if href.startswith("http://") or href.startswith("https://"):
            text = (a.get_text(strip=True) or cell.get_text(strip=True)) or ""
            return text, href
    return (cell.get_text(strip=True) or ""), None


def _parse_subjects_row_html(first_row) -> Dict[int, str]:
    subjects: Dict[int, str] = {}
    col = 0
    current_subject: str | None = None
    for cell in first_row.find_all(["td", "th"]):
        span = int(cell.get("colspan", 1))
        text = (cell.get_text(strip=True) or "").strip()
        if text and text not in ("#", "Дата"):
            current_subject = text
        for _ in range(span):
            if current_subject:
                subjects[col] = current_subject
            col += 1
    return subjects


def _parse_html(html: str) -> List[Homework]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")
    if len(rows) < 3:
        return []
    subjects = _parse_subjects_row_html(rows[0])
    subgroups: Dict[int, str] = {}
    for i, cell in enumerate(rows[1].find_all(["td", "th"])):
        text = (cell.get_text(strip=True) or "").strip()
        if text:
            subgroups[i] = text
    cols = [c for c in subjects if c in subgroups]
    if not cols:
        return []
    today = date.today()
    end_date = today + timedelta(days=14)
    result: List[Homework] = []
    for row in rows[2:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_date = _parse_date((cells[0].get_text(strip=True) or ""))
        if not row_date or row_date < today or row_date > end_date:
            continue
        for col in cols:
            if col >= len(cells):
                continue
            text, link = _parse_cell_link(cells[col])
            if not text:
                continue
            result.append(Homework(
                subject=subjects[col],
                date=row_date,
                subgroup=subgroups[col],
                content=text,
                link=link,
            ))
    return result


def _parse_csv(raw: str) -> List[Homework]:
    raw = raw.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 3:
        return []
    row0, row1 = rows[0], rows[1]
    subjects: Dict[int, str] = {}
    current_subject = None
    for i in range(1, len(row0)):
        cell = (row0[i] or "").strip()
        if cell and cell not in ("#", "Дата"):
            current_subject = cell
        if current_subject:
            subjects[i] = current_subject
    subgroups: Dict[int, str] = {}
    for i in range(1, len(row1)):
        cell = (row1[i] or "").strip()
        if cell:
            subgroups[i] = cell
    cols = [c for c in subjects if c in subgroups]
    if not cols:
        return []
    today = date.today()
    end_date = today + timedelta(days=14)
    result: List[Homework] = []
    for row in rows[2:]:
        if not row:
            continue
        row_date = _parse_date(row[0] or "")
        if not row_date or row_date < today or row_date > end_date:
            continue
        for col in cols:
            if col >= len(row):
                continue
            text = (row[col] or "").strip()
            if not text:
                continue
            result.append(Homework(
                subject=subjects[col],
                date=row_date,
                subgroup=subgroups[col],
                content=text,
                link=None,
            ))
    return result


async def parse_homework() -> List[Homework]:
    html = await fetch_sheet_html()
    if html:
        return _parse_html(html)
    raw = await fetch_sheet_csv()
    return _parse_csv(raw)
