"""Script to promote a user to admin role."""
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy.future import select

async def make_admin(username: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalars().first()
        
        if not user:
            print(f"User '{username}' not found.")
            return
        
        user.is_admin = True
        await db.commit()
        print(f"User '{username}' is now an admin.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    asyncio.run(make_admin(username))
