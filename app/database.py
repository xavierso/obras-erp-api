"""
Conexión a PostgreSQL con SQLAlchemy 2.0 en modo async.

Diferencia clave respecto al bot de Telegram original:
- Allí se usaba un engine síncrono (create_engine) con SQLite.
- Aquí usamos create_async_engine + AsyncSession, porque FastAPI
  corre sobre un event loop async y cada request debe poder
  hacer I/O de base de datos sin bloquear a los demás.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Clase base para todos los modelos, igual que en el proyecto original."""
    pass


engine = create_async_engine(
    settings.get_database_url,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    Dependency de FastAPI: entrega una sesión de BD por request
    y la cierra automáticamente al terminar.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """
    Crea las tablas si no existen.
    En el siguiente bloque esto se sustituirá por migraciones con Alembic,
    pero sirve para arrancar y probar rápido este primer bloque.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
