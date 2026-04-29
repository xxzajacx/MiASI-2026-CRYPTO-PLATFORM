import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE orders ADD COLUMN side VARCHAR DEFAULT 'SELL'"))
            print("Successfully added 'side' column to 'orders' table.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column 'side' already exists.")
            else:
                print(f"Error migrating: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
