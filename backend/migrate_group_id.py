import asyncio
import uuid
from app.core.database import engine
from sqlalchemy import text

async def migrate():
    print("Rozpoczynanie migracji: dodawanie kolumny 'group_id' do tabeli 'orders'...")
    try:
        async with engine.begin() as conn:
            # Dodanie kolumny group_id
            await conn.execute(text("ALTER TABLE orders ADD COLUMN group_id VARCHAR(50)"))
        print("Migracja zakończona sukcesem!")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Kolumna 'group_id' już istnieje. Pominięto.")
        else:
            print(f"Błąd podczas migracji: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
