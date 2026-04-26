import sqlite3
import asyncio
from config import DATABASE

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            credits INTEGER DEFAULT 0,
            total_queries INTEGER DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_data USING fts5(
            content,  -- все данные в одной строке (json или конкатенация полей)
            phone,
            email,
            full_name,
            nickname,
            address,
            passport,
            birth_date
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS raw_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            email TEXT,
            full_name TEXT,
            nickname TEXT,
            address TEXT,
            passport TEXT,
            birth_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(tg_id: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT credits, total_queries FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return {"credits": row[0], "total_queries": row[1]} if row else None

def create_user(tg_id: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (tg_id, credits) VALUES (?, 0)", (tg_id,))
    conn.commit()
    conn.close()

def add_credits(tg_id: int, amount: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE tg_id = ?", (amount, tg_id))
    conn.commit()
    conn.close()

def deduct_credits(tg_id: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits - 1, total_queries = total_queries + 1 WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def add_history(tg_id: int, query: str, result: str):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO history (user_id, query, result) VALUES (?, ?, ?)", (tg_id, query, result))
    conn.commit()
    conn.close()

def get_history(tg_id: int, limit: int = 10):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT query, result, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (tg_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT tg_id, credits, total_queries FROM users")
    rows = c.fetchall()
    conn.close()
    return [{"tg_id": r[0], "credits": r[1], "total_queries": r[2]} for r in rows]

def insert_record(record: dict):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO raw_data (phone, email, full_name, nickname, address, passport, birth_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (record.get('phone'), record.get('email'), record.get('full_name'), record.get('nickname'),
          record.get('address'), record.get('passport'), record.get('birth_date')))
    rowid = c.lastrowid
    # построим полный текст для fts
    content = ' '.join(str(v) for v in record.values() if v)
    c.execute('''
        INSERT INTO fts_data (rowid, content, phone, email, full_name, nickname, address, passport, birth_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (rowid, content, record.get('phone'), record.get('email'), record.get('full_name'),
          record.get('nickname'), record.get('address'), record.get('passport'), record.get('birth_date')))
    conn.commit()
    conn.close()

def search_fts(query: str):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # ищем по всем полям
    sql = '''
        SELECT raw_data.phone, raw_data.email, raw_data.full_name, raw_data.nickname,
               raw_data.address, raw_data.passport, raw_data.birth_date
        FROM fts_data
        JOIN raw_data ON fts_data.rowid = raw_data.id
        WHERE fts_data MATCH ?
        LIMIT 20
    '''
    c.execute(sql, (query,))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append({
            'phone': row[0], 'email': row[1], 'full_name': row[2], 'nickname': row[3],
            'address': row[4], 'passport': row[5], 'birth_date': row[6]
        })
    return result
