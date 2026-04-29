import asyncio
from app.core.database import engine
from sqlalchemy import text

async def migrate():
    print("Rozpoczynanie migracji: dodawanie kolumny 'leverage' do tabeli 'orders'...")
    try:
        async with engine.begin() as conn:
            # Sprawdzenie czy kolumna już istnieje (opcjonalnie, ale bezpieczniej)
            await conn.execute(text("ALTER TABLE orders ADD COLUMN leverage INTEGER DEFAULT 1"))
        print("Migracja zakończona sukcesem!")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Kolumna 'leverage' już istnieje. Pomiinięto.")
        else:
            print(f"Błąd podczas migracji: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
