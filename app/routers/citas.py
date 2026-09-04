"""
CRUD de citas/recordatorios programados. Restringido a admins — la
programación y gestión de citas no forma parte del rol Inspector.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_director, get_empresa_id
from app.database import get_db
from app.models.cita_visita import CitaVisita, EstadoCita
from app.models.obra import Obra
from app.models.usuario import Usuario, RolUsuario
from app.schemas.cita_visita import (
    CitaVisitaCreate,
    CitaVisitaEstadoUpdate,
    CitaVisitaOut,
    CitaVisitaUpdate,
)
from app.services.cita_service import calcular_momento_recordatorio

router = APIRouter(prefix="/citas", tags=["Citas y Recordatorios"])


async def _obtener_cita_de_la_empresa(cita_id: int, empresa_id: int, db: AsyncSession) -> CitaVisita:
    result = await db.execute(
        select(CitaVisita).where(CitaVisita.id == cita_id, CitaVisita.empresa_id == empresa_id)
    )
    cita = result.scalar_one_or_none()
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return cita


@router.post("", response_model=CitaVisitaOut, status_code=status.HTTP_201_CREATED)
async def crear_cita(
    datos: CitaVisitaCreate,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    if datos.obra_id is not None:
        result = await db.execute(
            select(Obra).where(Obra.id == datos.obra_id, Obra.empresa_id == empresa_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada"
            )

    momento_recordatorio = calcular_momento_recordatorio(
        datos.fecha_hora, datos.recordatorio_minutos_antes
    )

    nueva_cita = CitaVisita(
        obra_id=datos.obra_id,
        nombre_referencia=datos.nombre_referencia,
        empresa_id=empresa_id,
        usuario_id=admin.id,
        fecha_hora=datos.fecha_hora,
        notas=datos.notas,
        recordatorio_minutos_antes=datos.recordatorio_minutos_antes,
        momento_recordatorio=momento_recordatorio,
    )
    db.add(nueva_cita)
    await db.commit()
    await db.refresh(nueva_cita)
    return nueva_cita


@router.get("", response_model=list[CitaVisitaOut])
async def listar_citas(
    estado: EstadoCita | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    obra_id: int | None = None,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    query = select(CitaVisita).where(CitaVisita.empresa_id == empresa_id)
    if estado is not None:
        query = query.where(CitaVisita.estado == estado)
    if desde is not None:
        query = query.where(CitaVisita.fecha_hora >= desde)
    if hasta is not None:
        query = query.where(CitaVisita.fecha_hora <= hasta)
    if obra_id is not None:
        query = query.where(CitaVisita.obra_id == obra_id)

    result = await db.execute(query.order_by(CitaVisita.fecha_hora.asc()))
    return result.scalars().all()


@router.get("/{cita_id}", response_model=CitaVisitaOut)
async def consultar_cita(
    cita_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    return await _obtener_cita_de_la_empresa(cita_id, empresa_id, db)


@router.patch("/{cita_id}", response_model=CitaVisitaOut)
async def reprogramar_cita(
    cita_id: int,
    datos: CitaVisitaUpdate,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, empresa_id, db)

    if datos.fecha_hora is not None:
        cita.fecha_hora = datos.fecha_hora
    if datos.notas is not None:
        cita.notas = datos.notas
    if datos.recordatorio_minutos_antes is not None:
        cita.recordatorio_minutos_antes = datos.recordatorio_minutos_antes

    # Si cambió la fecha o el recordatorio, se recalcula el momento exacto
    # y se resetea el flag de enviado -> el scheduler volverá a considerarla.
    if datos.fecha_hora is not None or datos.recordatorio_minutos_antes is not None:
        cita.momento_recordatorio = calcular_momento_recordatorio(
            cita.fecha_hora, cita.recordatorio_minutos_antes
        )
        cita.recordatorio_enviado = False

    await db.commit()
    await db.refresh(cita)
    return cita


@router.patch("/{cita_id}/estado", response_model=CitaVisitaOut)
async def cambiar_estado_cita(
    cita_id: int,
    datos: CitaVisitaEstadoUpdate,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, empresa_id, db)
    cita.estado = datos.estado
    await db.commit()
    await db.refresh(cita)
    return cita


@router.delete("/{cita_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cita(
    cita_id: int,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, empresa_id, db)
    await db.delete(cita)
    await db.commit()
