"""Migration script to add is_admin column to users table."""
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_admin'
        """))
        
        if result.first() is None:
            print("Adding is_admin column to users table...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE
            """))
            print("Migration completed successfully!")
        else:
            print("Column is_admin already exists. Skipping migration.")

if __name__ == "__main__":
    asyncio.run(migrate())
