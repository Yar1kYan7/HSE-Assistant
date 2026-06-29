import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL не задан в переменных окружения!")
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        logger.info("Подключение к PostgreSQL установлено")
    return _pool

async def init_db():
    """Создаёт все необходимые таблицы."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                subgroup TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS faq_entries (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id SERIAL PRIMARY KEY,
                subgroup VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                start_time VARCHAR(10) NOT NULL,
                end_time VARCHAR(10) NOT NULL,
                title VARCHAR(200) NOT NULL,
                link TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                subject VARCHAR(200) NOT NULL,
                date DATE NOT NULL,
                subgroup VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                link TEXT
            )
        """)
        logger.info("Все таблицы созданы (или уже существуют)")


async def is_subscribed(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на уведомления."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM subscriptions WHERE user_id = $1",
            user_id
        )
        return row is not None

async def add_subscription(user_id: int):
    """Добавляет пользователя в список подписок."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO subscriptions (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
            user_id
        )

async def remove_subscription(user_id: int):
    """Удаляет пользователя из списка подписок."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM subscriptions WHERE user_id = $1",
            user_id
        )

async def get_user_subgroup(user_id: int) -> str | None:
    """Возвращает подгруппу пользователя."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT subgroup FROM users WHERE user_id = $1",
            user_id
        )
        return row["subgroup"] if row else None

async def set_user_subgroup(user_id: int, subgroup: str):
    """Устанавливает подгруппу пользователя."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, subgroup) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET subgroup = $2",
            user_id, subgroup
        )

async def get_all_subscriptions() -> list[tuple[int, str | None]]:
    """Возвращает список всех подписчиков с их подгруппами."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.user_id, u.subgroup
            FROM subscriptions s
            LEFT JOIN users u ON s.user_id = u.user_id
            """
        )
        return [(row["user_id"], row["subgroup"]) for row in rows]

async def get_all_user_ids() -> list[int]:
    """Возвращает список всех пользователей."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [row["user_id"] for row in rows]



# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С FAQ ==========

async def search_faq(query: str) -> list[dict]:
    """
    Поиск по FAQ по ключевым словам.
    Возвращает список записей, где query встречается в question или keywords.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, question, answer, keywords
            FROM faq_entries
            WHERE question ILIKE $1 OR keywords ILIKE $1
            ORDER BY id
            LIMIT 5
            """,
            f"%{query}%"
        )
        return [dict(row) for row in rows]


async def add_faq_entry(question: str, answer: str, keywords: str) -> bool:
    """Добавляет новую запись в FAQ."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO faq_entries (question, answer, keywords)
            VALUES ($1, $2, $3)
            """,
            question, answer, keywords
        )
        return True


async def delete_faq_entry(entry_id: int) -> bool:
    """Удаляет запись из FAQ по ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM faq_entries WHERE id = $1",
            entry_id
        )
        return result != "DELETE 0"