import sqlite3
from pathlib import Path
from passlib.context import CryptContext
from uuid import uuid4
from datetime import datetime
import aiosqlite

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
DB_PATH = Path("backend/database.db")

async def get_db():
    return await aiosqlite.connect(str(DB_PATH))

async def init_db():
    conn = await get_db()
    
    # Create users table
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    
    await conn.commit()
    await conn.close()

async def create_user(username: str, password: str):
    conn = await get_db()
    
    user_id = str(uuid4())
    hashed_password = pwd_context.hash(password)
    created_at = datetime.utcnow()
    
    try:
        await conn.execute(
            "INSERT INTO users (id, username, hashed_password, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, hashed_password, created_at)
        )
        await conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        await conn.close()

async def get_user(username: str):
    conn = await get_db()
    
    async with conn.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
        user = await cursor.fetchone()
    
    await conn.close()
    
    return dict(user) if user else None

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password) 