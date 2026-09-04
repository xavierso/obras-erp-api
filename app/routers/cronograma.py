from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.actividad_cronograma import ActividadCronograma
from app.schemas.actividad_cronograma import (
    ActividadCronogramaCreate,
    ActividadCronogramaResponse,
    ActividadCronogramaUpdate,
)
from app.models.obra import Obra
from app.core.deps import get_current_user, require_director
from app.services.cronograma_service import actualizar_progreso_obra

router = APIRouter(prefix="/cronograma", tags=["cronograma"])


@router.post("/", response_model=ActividadCronogramaResponse, status_code=status.HTTP_201_CREATED)
async def create_actividad(
    actividad: ActividadCronogramaCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obra_result = await db.execute(select(Obra).where(Obra.id == actividad.obra_id, Obra.empresa_id == current_user.empresa_id))
    obra = obra_result.scalar_one_or_none()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    data = actividad.model_dump()
    preds_ids = data.pop("predecesoras_ids", [])
    data["empresa_id"] = current_user.empresa_id
    
    db_actividad = ActividadCronograma(**data)
    
    if preds_ids:
        preds_result = await db.execute(select(ActividadCronograma).where(ActividadCronograma.id.in_(preds_ids), ActividadCronograma.empresa_id == current_user.empresa_id))
        db_actividad.predecesoras = list(preds_result.scalars().all())

    db.add(db_actividad)
    await db.commit()
    await db.refresh(db_actividad)
    
    # Reload with selectinload to avoid LazyLoading error on property
    result = await db.execute(
        select(ActividadCronograma)
        .options(selectinload(ActividadCronograma.predecesoras))
        .where(ActividadCronograma.id == db_actividad.id)
    )
    db_actividad_loaded = result.scalar_one()

    await actualizar_progreso_obra(db_actividad_loaded.obra_id, db)
    return db_actividad_loaded


@router.get("/obra/{obra_id}", response_model=List[ActividadCronogramaResponse])
async def get_actividades_por_obra(
    obra_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obra_result = await db.execute(select(Obra).where(Obra.id == obra_id, Obra.empresa_id == current_user.empresa_id))
    if not obra_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Obra no encontrada")
        
    result = await db.execute(
        select(ActividadCronograma)
        .options(selectinload(ActividadCronograma.predecesoras))
        .where(ActividadCronograma.obra_id == obra_id, ActividadCronograma.empresa_id == current_user.empresa_id)
        .order_by(ActividadCronograma.fecha_inicio)
    )
    actividades = result.scalars().all()
    return actividades


@router.get("/{actividad_id}", response_model=ActividadCronogramaResponse)
async def get_actividad(
    actividad_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(ActividadCronograma)
        .options(selectinload(ActividadCronograma.predecesoras))
        .where(ActividadCronograma.id == actividad_id, ActividadCronograma.empresa_id == current_user.empresa_id)
    )
    actividad = result.scalar_one_or_none()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    return actividad


@router.put("/{actividad_id}", response_model=ActividadCronogramaResponse)
async def update_actividad(
    actividad_id: int,
    actividad_update: ActividadCronogramaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(ActividadCronograma)
        .options(selectinload(ActividadCronograma.predecesoras))
        .where(ActividadCronograma.id == actividad_id, ActividadCronograma.empresa_id == current_user.empresa_id)
    )
    actividad = result.scalar_one_or_none()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    update_data = actividad_update.model_dump(exclude_unset=True)
    
    if "predecesoras_ids" in update_data:
        preds_ids = update_data.pop("predecesoras_ids")
        if preds_ids is not None:
            preds_result = await db.execute(select(ActividadCronograma).where(ActividadCronograma.id.in_(preds_ids), ActividadCronograma.empresa_id == current_user.empresa_id))
            actividad.predecesoras = list(preds_result.scalars().all())
        else:
            actividad.predecesoras = []

    for key, value in update_data.items():
        setattr(actividad, key, value)

    await db.commit()
    await db.refresh(actividad)
    
    # Reload
    result_reload = await db.execute(
        select(ActividadCronograma)
        .options(selectinload(ActividadCronograma.predecesoras))
        .where(ActividadCronograma.id == actividad_id)
    )
    actividad_loaded = result_reload.scalar_one()

    await actualizar_progreso_obra(actividad_loaded.obra_id, db)
    return actividad_loaded


@router.delete("/{actividad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actividad(
    actividad_id: int,
    db: AsyncSession = Depends(get_db),
    director=Depends(require_director),
):
    result = await db.execute(select(ActividadCronograma).where(ActividadCronograma.id == actividad_id, ActividadCronograma.empresa_id == director.empresa_id))
    actividad = result.scalar_one_or_none()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    obra_id = actividad.obra_id
    await db.delete(actividad)
    await db.commit()
    await actualizar_progreso_obra(obra_id, db)
    return None

