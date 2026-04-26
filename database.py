import asyncpg
from config import POSTGRES_DSN

async def get_pool():
    return await asyncpg.create_pool(POSTGRES_DSN)

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                tg_id BIGINT PRIMARY KEY,
                credits INT DEFAULT 0,
                total_queries INT DEFAULT 0,
                registered_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                query TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                original_name TEXT,
                size BIGINT,
                status TEXT,
                uploaded_by BIGINT,
                uploaded_at TIMESTAMP DEFAULT NOW()
            )
        ''')
    await pool.close()

async def get_user(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT credits, total_queries FROM users WHERE tg_id = $1", tg_id)
        return {"credits": row[0], "total_queries": row[1]} if row else None

async def create_user(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (tg_id, credits) VALUES ($1, 0) ON CONFLICT DO NOTHING", tg_id)

async def add_credits(tg_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET credits = credits + $1 WHERE tg_id = $2", amount, tg_id)

async def deduct_credits(tg_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET credits = credits - 1, total_queries = total_queries + 1 WHERE tg_id = $1", tg_id)

async def add_history(tg_id: int, query: str, result: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO history (user_id, query, result) VALUES ($1, $2, $3)", tg_id, query, result)

async def get_history(tg_id: int, limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT query, result, created_at FROM history WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2", tg_id, limit)
        return rows

async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT tg_id, credits, total_queries FROM users")
        return rows
