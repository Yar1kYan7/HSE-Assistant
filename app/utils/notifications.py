import asyncio
import html
import logging
import re
from typing import List

from aiogram import Bot
from aiogram.types import MessageEntity
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramServerError,
)

from app.parser.models import Homework

logger = logging.getLogger(__name__)

_ENTITY_TAGS = {
    "bold": ("<b>", "</b>"),
    "italic": ("<i>", "</i>"),
    "underline": ("<u>", "</u>"),
    "strikethrough": ("<s>", "</s>"),
    "spoiler": ("<tg-spoiler>", "</tg-spoiler>"),
    "code": ("<code>", "</code>"),
}


def _entity_close_tag(kind: str, stack_item) -> str:
    if kind in _ENTITY_TAGS:
        return _ENTITY_TAGS[kind][1]
    if kind == "text_link":
        return "</a>"
    if kind == "pre":
        return "</code></pre>"
    return ""


def _entity_open_tag(kind: str, extra) -> str:
    if kind in _ENTITY_TAGS:
        return _ENTITY_TAGS[kind][0]
    if kind == "text_link" and extra:
        return f'<a href="{html.escape(extra)}">'
    if kind == "pre":
        return f'<pre><code class="language-{html.escape(extra)}">' if extra else "<pre><code>"
    return ""


def message_entities_to_html(text: str, entities: List[MessageEntity] | None) -> str:
    if not text:
        return ""
    if not entities:
        return html.escape(text)
    events = []
    for e in entities:
        end = e.offset + e.length
        if e.offset < 0 or end > len(text):
            continue
        kind = e.type if isinstance(e.type, str) else getattr(e.type, "value", str(e.type))
        if kind in _ENTITY_TAGS:
            events.append((e.offset, "open", kind, None))
            events.append((end, "close", kind, None))
        elif kind == "text_link" and getattr(e, "url", None):
            events.append((e.offset, "open", "text_link", e.url))
            events.append((end, "close", "text_link", None))
        elif kind == "pre":
            lang = getattr(e, "language", None) or ""
            events.append((e.offset, "open", "pre", lang))
            events.append((end, "close", "pre", None))
    events.sort(key=lambda x: (x[0], 0 if x[1] == "open" else 1))
    stack = []
    result = []
    pos = 0
    for idx, action, kind, extra in events:
        if idx > pos:
            result.append(html.escape(text[pos:idx]))
            pos = idx
        if action == "open":
            result.append(_entity_open_tag(kind, extra))
            stack.append((kind, extra))
        else:
            reopened = []
            while stack:
                last_kind, last_extra = stack.pop()
                if last_kind == kind:
                    result.append(_entity_close_tag(kind, None))
                    break
                result.append(_entity_close_tag(last_kind, None))
                reopened.append((last_kind, last_extra))
            for k, ex in reversed(reopened):
                result.append(_entity_open_tag(k, ex))
                stack.append((k, ex))
    if pos < len(text):
        result.append(html.escape(text[pos:]))
    for kind, _ in reversed(stack):
        result.append(_entity_close_tag(kind, None))
    return "".join(result)


WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def _content_display(hw: Homework) -> str:
    content = hw.content
    url_pattern = r'https?://[^\s\)]+'
    match = re.search(url_pattern, content)
    
    if match:
        url = match.group(0)
        text_before = content[:match.start()].strip()
        if text_before.endswith('('):
            text_before = text_before[:-1].strip()
        if not text_before:
            text_before = "ДЗ"
        esc_text = html.escape(text_before)
        return f'<a href="{url}">{esc_text}</a>'
    
    return html.escape(content)


async def send_safe(bot: Bot, user_id: int, text: str) -> bool:
    try:
        await bot.send_message(user_id, text)
        return True
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await bot.send_message(user_id, text)
            return True
        except (TelegramBadRequest, TelegramForbiddenError, TelegramServerError):
            return False
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        err = str(e).lower()
        if "chat not found" in err or "blocked" in err or "forbidden" in err:
            from app.database.db import remove_subscription
            try:
                await remove_subscription(user_id)
            except Exception:
                pass
        return False
    except TelegramServerError:
        return False


def format_homeworks(
    homeworks: List[Homework],
    subgroup: str | None = None,
    header: str | None = None
) -> List[str]:
    if not homeworks:
        return []
    
    if header is None:
        if subgroup:
            header = f"<b>📚 ДЗ для {subgroup}</b>\n<i>🗓 Ближайшие 2 недели</i>"
        else:
            header = "<b>📚 Домашние задания</b>\n<i>🗓 Ближайшие 2 недели</i>"
    
    sorted_homeworks = sorted(homeworks, key=lambda x: (x.date, x.subject))
    parts = [header]
    last_date = None
    
    for homework in sorted_homeworks:
        if last_date != homework.date:
            weekday = WEEKDAYS_RU[homework.date.weekday()]
            parts.append(f"\n<b>{homework.date.strftime('%d.%m.%Y')} | {weekday}</b>")
            last_date = homework.date
        parts.append(f"└ <b>{homework.subject}</b>")
        content = _content_display(homework)
        if '<a href=' in content:
            parts.append(f"   └ {content}")
        else:
            parts.append(f"   └ <code>{content}</code>")
    
    text = "\n".join(parts)
    
    if len(text) <= 4096:
        return [text]
    
    result = []
    current = [header]
    current_len = len(header)
    
    for homework in sorted_homeworks:
        weekday = WEEKDAYS_RU[homework.date.weekday()]
        content = _content_display(homework)
        if '<a href=' in content:
            content_line = f"   └ {content}"
        else:
            content_line = f"   └ <code>{content}</code>"
        homework_text = f"\n<b>{homework.date.strftime('%d.%m.%Y')} | {weekday}</b>\n└ <b>{homework.subject}</b>\n{content_line}"
        if current_len + len(homework_text) > 4000:
            result.append("\n".join(current))
            current = [homework_text]
            current_len = len(homework_text)
        else:
            current.append(homework_text)
            current_len += len(homework_text)
    
    if current:
        result.append("\n".join(current))
    
    return result


def format_deadlines_tomorrow(homeworks: List[Homework], subgroup: str | None = None) -> str:
    if not homeworks:
        return ""
    header = f"⏰ <b>Завтра дедлайны</b>" + (f" ({subgroup})" if subgroup else "") + "\n\n"
    parts = [header]
    for h in sorted(homeworks, key=lambda x: x.subject):
        content = _content_display(h)
        if "<a href=" in content:
            parts.append(f"• <b>{h.subject}</b>: {content}")
        else:
            parts.append(f"• <b>{h.subject}</b>: <code>{content}</code>")
    return "\n".join(parts)


async def notify_deadlines_tomorrow(
    bot: Bot,
    subscribers: List[tuple[int, str | None]],
    homeworks_tomorrow: List[Homework],
):
    if not homeworks_tomorrow or not subscribers:
        return
    for user_id, subgroup in subscribers:
        if subgroup:
            filtered = [h for h in homeworks_tomorrow if h.subgroup == subgroup or h.subgroup == "Все"]
        else:
            filtered = homeworks_tomorrow
        if not filtered:
            continue
        text = format_deadlines_tomorrow(filtered, subgroup)
        if not await send_safe(bot, user_id, text):
            continue
        await asyncio.sleep(0.05)


async def notify_subscribers(
    bot: Bot,
    subscribers: List[tuple[int, str | None]],
    new_homeworks: List[Homework]
):
    if not new_homeworks or not subscribers:
        return
    
    for user_id, subgroup in subscribers:
        try:
            if subgroup:
                filtered = [h for h in new_homeworks if h.subgroup == subgroup or h.subgroup == "Все"]
            else:
                filtered = new_homeworks
            
            if not filtered:
                continue
            
            messages = format_homeworks(
                filtered,
                subgroup=subgroup,
                header=f"<b>🔔 Новые ДЗ для {subgroup}</b>" if subgroup else None
            )
            for msg in messages:
                if not await send_safe(bot, user_id, msg):
                    break
                await asyncio.sleep(0.05)
        except Exception as e:
            error_str = str(e).lower()
            if "blocked" in error_str or "forbidden" in error_str:
                logger.debug(f"Пользователь {user_id} заблокировал бота")
                continue
            logger.warning(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
