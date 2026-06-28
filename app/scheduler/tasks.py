import logging
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.parser.google_sheets import parse_homework
from app.parser.hse_schedule import get_today_schedule_message
from app.database.storage import load_homeworks, save_homeworks
from app.database.db import get_all_subscriptions
from app.utils.notifications import notify_subscribers, notify_deadlines_tomorrow
from app.bot.keyboards import get_schedule_link_keyboard
from app.config import TIMEZONE, ADMIN_TG

logger = logging.getLogger(__name__)

_bot: Bot | None = None


async def update_homeworks():
    try:
        new_hw = await parse_homework()
        old_hw = load_homeworks()

        new_hw_list = list(set(new_hw) - set(old_hw))
        save_homeworks(new_hw)

        if new_hw_list and _bot:
            subs = await get_all_subscriptions()
            if subs:
                await notify_subscribers(_bot, subs, new_hw_list)
    except Exception as e:
        error_str = str(e).lower()
        if "blocked" in error_str or "forbidden" in error_str:
            logger.debug(f"Пользователь заблокировал бота: {e}")
            return

        logger.error(f"Ошибка обновления ДЗ: {e}", exc_info=True)
        if ADMIN_TG and _bot:
            try:
                await _bot.send_message(ADMIN_TG, f"❌ Ошибка обновления ДЗ: {e}")
            except Exception:
                pass


async def check_deadlines_tomorrow():
    try:
        homeworks = load_homeworks()
        tz = pytz.timezone(TIMEZONE)
        tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
        deadline_hw = [h for h in homeworks if h.date == tomorrow]
        if not deadline_hw or not _bot:
            return
        subs = await get_all_subscriptions()
        if subs:
            await notify_deadlines_tomorrow(_bot, subs, deadline_hw)
    except Exception as e:
        error_str = str(e).lower()
        if "blocked" in error_str or "forbidden" in error_str:
            logger.debug(f"Пользователь заблокировал бота: {e}")
            return
        logger.error(f"Ошибка проверки дедлайнов: {e}", exc_info=True)
        if ADMIN_TG and _bot:
            try:
                await _bot.send_message(ADMIN_TG, f"❌ Ошибка дедлайнов: {e}")
            except Exception:
                pass


async def send_today_schedule():
    try:
        if not _bot:
            return

        subs = await get_all_subscriptions()
        if not subs:
            return

        subgroup_cache: dict[str | None, str] = {}
        sent = 0
        for user_id, subgroup in subs:
            try:
                if not subgroup:
                    continue
                if subgroup not in subgroup_cache:
                    subgroup_cache[subgroup] = await get_today_schedule_message(
                        subgroup=subgroup
                    )
                text = subgroup_cache[subgroup]
                await _bot.send_message(
                    user_id,
                    text,
                    disable_web_page_preview=True,
                    reply_markup=get_schedule_link_keyboard(),
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                error_str = str(e).lower()
                if "blocked" in error_str or "forbidden" in error_str:
                    logger.debug(f"Пользователь {user_id} заблокировал бота")
                    continue
                logger.warning(
                    f"Ошибка отправки расписания пользователю {user_id}: {e}"
                )

        logger.info("Расписание на сегодня отправлено: %s пользователям", sent)
    except Exception as e:
        logger.error(f"Ошибка отправки расписания на сегодня: {e}", exc_info=True)
        if ADMIN_TG and _bot:
            try:
                await _bot.send_message(ADMIN_TG, f"❌ Ошибка отправки расписания: {e}")
            except Exception:
                pass


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    global _bot
    _bot = bot

    scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))

    scheduler.add_job(
        update_homeworks, trigger=CronTrigger(minute=0), id="update_hourly"
    )
    scheduler.add_job(
        check_deadlines_tomorrow,
        trigger=CronTrigger(hour=6, minute=30),
        id="deadlines_tomorrow",
    )
    scheduler.add_job(
        send_today_schedule, trigger=CronTrigger(hour=7, minute=0), id="today_schedule"
    )

    return scheduler
