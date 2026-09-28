from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.core.deps import get_current_user, get_empresa_id
from app.models.usuario import Usuario
from app.models.evento_actividad import EventoActividad, EventoActividadLectura
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

class NotificacionOut(BaseModel):
    id: int
    tipo_evento: str
    mensaje: str
    created_at: datetime
    leida: bool

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[NotificacionOut])
async def obtener_notificaciones(
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    # Fetch events for the company
    result = await db.execute(
        select(EventoActividad)
        .where(EventoActividad.empresa_id == empresa_id)
        .order_by(EventoActividad.created_at.desc())
        .limit(50)
    )
    eventos = result.scalars().all()

    # Fetch read status for this user
    evento_ids = [e.id for e in eventos]
    lecturas = []
    if evento_ids:
        res_lecturas = await db.execute(
            select(EventoActividadLectura.evento_id)
            .where(
                EventoActividadLectura.evento_id.in_(evento_ids),
                EventoActividadLectura.usuario_id == usuario.id
            )
        )
        lecturas = res_lecturas.scalars().all()

    leidas_set = set(lecturas)

    return [
        NotificacionOut(
            id=e.id,
            tipo_evento=e.tipo_evento,
            mensaje=e.mensaje,
            created_at=e.created_at,
            leida=(e.id in leidas_set)
        )
        for e in eventos
    ]

@router.post("/{evento_id}/leer", status_code=204)
async def marcar_leida(
    evento_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if already read
    result = await db.execute(
        select(EventoActividadLectura)
        .where(
            EventoActividadLectura.evento_id == evento_id,
            EventoActividadLectura.usuario_id == usuario.id
        )
    )
    lectura = result.scalar_one_or_none()
    
    if not lectura:
        nueva_lectura = EventoActividadLectura(
            evento_id=evento_id,
            usuario_id=usuario.id
        )
        db.add(nueva_lectura)
        await db.commit()
