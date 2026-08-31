from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.models.presupuesto import Presupuesto, EstadoPresupuesto
from app.schemas.presupuesto import PresupuestoOut, PresupuestoCreate, PresupuestoUpdate, PresupuestoResumenOut, GenerarCronogramaReq
from app.services.presupuesto_service import crear_presupuesto, get_presupuesto, aprobar_presupuesto, generar_cronograma_desde_presupuesto


router = APIRouter(prefix="/presupuestos", tags=["Presupuestos"])

@router.post("/", response_model=PresupuestoOut, status_code=status.HTTP_201_CREATED)
async def create_presupuesto(
    data: PresupuestoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await crear_presupuesto(db, data, usuario.id)

from sqlalchemy.orm import selectinload
from app.models.presupuesto import CapituloPresupuesto

@router.get("/", response_model=List[PresupuestoResumenOut])
async def list_todos_presupuestos(
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    stmt = select(Presupuesto).options(
        selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas)
    ).order_by(Presupuesto.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/obra/{obra_id}", response_model=List[PresupuestoResumenOut])
async def list_presupuestos_obra(
    obra_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    stmt = select(Presupuesto).where(Presupuesto.obra_id == obra_id).options(
        selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas)
    ).order_by(Presupuesto.version.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{presupuesto_id}", response_model=PresupuestoOut)
async def read_presupuesto(
    presupuesto_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    presupuesto = await get_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return presupuesto


from app.services.presupuesto_service import actualizar_presupuesto

@router.put("/{presupuesto_id}", response_model=PresupuestoOut)
async def update_presupuesto(
    presupuesto_id: int,
    data: PresupuestoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await actualizar_presupuesto(db, presupuesto_id, data)

from app.schemas.presupuesto import PresupuestoAprobar, PresupuestoEstadoUpdate

@router.post("/{presupuesto_id}/aprobar", response_model=PresupuestoOut)
async def approve_presupuesto(
    presupuesto_id: int,
    data: PresupuestoAprobar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await aprobar_presupuesto(db, presupuesto_id, usuario.id, data.model_dump(exclude_unset=True))


from app.services.presupuesto_service import cambiar_estado_presupuesto

@router.put("/{presupuesto_id}/estado")
async def update_estado(
    presupuesto_id: int,
    data: PresupuestoEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    presupuesto = await cambiar_estado_presupuesto(db, presupuesto_id, data.estado)
    return {"id": presupuesto.id, "estado": presupuesto.estado.value, "message": "Estado actualizado"}


@router.post("/{presupuesto_id}/generar-cronograma")
async def generar_cronograma(
    presupuesto_id: int,
    req: GenerarCronogramaReq,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    partidas_ids = [item.partida_id for item in req.partidas]
    return await generar_cronograma_desde_presupuesto(db, presupuesto_id, partidas_ids, usuario.id)


from app.schemas.presupuesto import CapituloPresupuestoCreate, CapituloPresupuestoOut, PartidaPresupuestoCreate, PartidaPresupuestoOut, PartidaPresupuestoUpdate
from app.services.presupuesto_service import crear_capitulo, eliminar_capitulo, crear_partida, eliminar_partida, actualizar_partida

@router.post("/{presupuesto_id}/capitulos", response_model=CapituloPresupuestoOut)
async def add_capitulo(
    presupuesto_id: int,
    data: CapituloPresupuestoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await crear_capitulo(db, presupuesto_id, data)

@router.delete("/capitulos/{capitulo_id}")
async def delete_capitulo(
    capitulo_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await eliminar_capitulo(db, capitulo_id)


@router.post("/capitulos/{capitulo_id}/partidas", response_model=PartidaPresupuestoOut)
async def add_partida(
    capitulo_id: int,
    data: PartidaPresupuestoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await crear_partida(db, capitulo_id, data)

@router.delete("/partidas/{partida_id}")
async def delete_partida(
    partida_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await eliminar_partida(db, partida_id)

@router.put("/partidas/{partida_id}", response_model=PartidaPresupuestoOut)
async def update_partida_route(
    partida_id: int,
    data: PartidaPresupuestoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await actualizar_partida(db, partida_id, data)
