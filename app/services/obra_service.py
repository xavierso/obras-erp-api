"""
LÃ³gica de negocio de Obra, migrada desde bot_erp_obras/services/obra_service.py.

Se conserva el formato de cÃ³digo autogenerado del bot: OB-{AÃ‘O}-{secuencial}.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.obra import Obra


async def generar_codigo_obra(db: AsyncSession, empresa_id: int) -> str:
    """Genera el siguiente cÃ³digo Ãºnico del aÃ±o actual, ej. OB-2026-004."""
    anio = datetime.now(timezone.utc).year
    prefijo = f"OB-{anio}-"

    result = await db.execute(
        select(func.count()).select_from(Obra).where(Obra.codigo.like(f"{prefijo}%"), Obra.empresa_id == empresa_id)
    )
    cantidad = result.scalar_one()
    siguiente = cantidad + 1
    return f"{prefijo}{siguiente:03d}"

