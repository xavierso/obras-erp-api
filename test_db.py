import asyncio
from app.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as db:
        res = await db.execute(text("SELECT id, logo_ruta FROM empresas"))
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
