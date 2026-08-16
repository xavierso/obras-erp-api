"""
Lógica de negocio de Obra, migrada desde bot_erp_obras/services/obra_service.py.

Se conserva el formato de código autogenerado del bot: OB-{AÑO}-{secuencial}.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obra import Obra


async def generar_codigo_obra(db: AsyncSession) -> str:
    """Genera el siguiente código único del año actual, ej. OB-2026-004."""
    anio = datetime.now(timezone.utc).year
    prefijo = f"OB-{anio}-"

    result = await db.execute(
        select(func.count()).select_from(Obra).where(Obra.codigo.like(f"{prefijo}%"))
    )
    cantidad = result.scalar_one()
    siguiente = cantidad + 1
    return f"{prefijo}{siguiente:03d}"
