"""Migration script to add email and binance_api columns to users table."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine


async def migrate():
    columns_to_add = [
        ("email", "VARCHAR UNIQUE"),
        ("is_admin", "BOOLEAN DEFAULT FALSE"),
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("locked_until", "VARCHAR"),
        ("first_name", "VARCHAR DEFAULT ''"),
        ("last_name", "VARCHAR DEFAULT ''"),
        ("birth_date", "VARCHAR(10) DEFAULT '2000-01-01'"),
        ("binance_api_key", "VARCHAR"),
        ("binance_secret_key", "VARCHAR")
    ]
    
    for col, dtype in columns_to_add:
        async with engine.begin() as conn:
            try:
                await conn.execute(text(f"SELECT {col} FROM users LIMIT 1"))
                print(f"Column '{col}' already exists in users table.")
            except Exception:
                pass

        async with engine.begin() as conn:
            try:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {dtype}"))
                print(f"Successfully added '{col}' column to users table.")
            except Exception as e:
                pass


if __name__ == "__main__":
    asyncio.run(migrate())
