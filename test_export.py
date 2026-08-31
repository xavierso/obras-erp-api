import asyncio
from app.database import AsyncSessionLocal
from app.models.usuario import Usuario
from app.routers.exportacion import export_to_excel
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario).where(Usuario.rol == 'ADMIN'))
        admin = result.scalars().first()
        if not admin:
            print("No admin found")
            return
        
        print(f"Testing with admin {admin.id}")
        response = await export_to_excel(admin=admin, db=db)
        print("Response:", response)

if __name__ == "__main__":
    asyncio.run(main())
