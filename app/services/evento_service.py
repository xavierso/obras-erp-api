from sqlalchemy.ext.asyncio import AsyncSession
from app.models.evento_actividad import EventoActividad

async def registrar_evento(
    db: AsyncSession,
    empresa_id: int,
    tipo_evento: str,
    mensaje: str,
    entidad_tipo: str = None,
    entidad_id: int = None
):
    evento = EventoActividad(
        empresa_id=empresa_id,
        tipo_evento=tipo_evento,
        mensaje=mensaje,
        entidad_relacionada_tipo=entidad_tipo,
        entidad_relacionada_id=entidad_id
    )
    db.add(evento)
    # No hacemos commit aquí para que se integre en la transacción del endpoint
