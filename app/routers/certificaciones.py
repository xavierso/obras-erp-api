from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.models.certificacion import Certificacion
from app.schemas.certificacion import (
    CertificacionCreate, CertificacionUpdate, CertificacionOut,
    CertificacionResumenOut, CertificacionEstadoUpdate, LineaCertificacionUpdate
)
from app.services.certificacion_service import (
    get_certificacion_con_detalles, crear_certificacion, guardar_mediciones,
    cambiar_estado, get_certificacion_resumen_calculado
)

router = APIRouter(tags=["Certificaciones"])

@router.get("/presupuestos/{presupuesto_id}/certificaciones", response_model=List[CertificacionResumenOut])
async def list_certificaciones_presupuesto(
    presupuesto_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    res = await db.execute(
        select(Certificacion)
        .where(Certificacion.presupuesto_id == presupuesto_id)
        .order_by(Certificacion.numero.asc())
    )
    certificaciones = res.scalars().all()
    
    salida = []
    for cert in certificaciones:
        resumen = await get_certificacion_resumen_calculado(db, cert)
        item = CertificacionResumenOut.model_validate(cert)
        item.importe_actual = resumen['importe_actual']
        item.porcentaje_avance_total = resumen['porcentaje_avance_total']
        salida.append(item)
        
    return salida

@router.post("/presupuestos/{presupuesto_id}/certificaciones", response_model=CertificacionOut, status_code=status.HTTP_201_CREATED)
async def create_cert(
    presupuesto_id: int,
    data: CertificacionCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await crear_certificacion(db, presupuesto_id, data)

@router.get("/certificaciones/{certificacion_id}", response_model=CertificacionOut)
async def read_cert(
    certificacion_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await get_certificacion_con_detalles(db, certificacion_id)


@router.put("/certificaciones/{certificacion_id}/lineas", response_model=CertificacionOut)
async def update_lineas(
    certificacion_id: int,
    lineas: List[LineaCertificacionUpdate],
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await guardar_mediciones(db, certificacion_id, lineas)


@router.put("/certificaciones/{certificacion_id}/estado", response_model=CertificacionOut)
async def update_estado(
    certificacion_id: int,
    data: CertificacionEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return await cambiar_estado(db, certificacion_id, data.estado)
