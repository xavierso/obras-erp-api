from typing import List, Optional
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.certificacion import Certificacion, LineaCertificacion, EstadoCertificacion
from app.models.presupuesto import Presupuesto, PartidaPresupuesto, CapituloPresupuesto
from app.schemas.certificacion import CertificacionCreate, CertificacionUpdate, LineaCertificacionUpdate, CertificacionOut, LineaCertificacionOut

async def get_certificacion_resumen_calculado(db: AsyncSession, certificacion: Certificacion) -> dict:
    """Calcula importes resumen para listas de certificaciones sin cargar todas las líneas."""
    res = await db.execute(
        select(
            func.sum(LineaCertificacion.cantidad_actual * PartidaPresupuesto.precio_unitario)
        )
        .join(PartidaPresupuesto, LineaCertificacion.partida_id == PartidaPresupuesto.id)
        .where(LineaCertificacion.certificacion_id == certificacion.id)
    )
    importe_actual = res.scalar() or 0.0
    return {
        "importe_actual": importe_actual,
        "porcentaje_avance_total": 0.0 # Simplificado para el resumen
    }


async def get_certificacion_con_detalles(db: AsyncSession, certificacion_id: int) -> CertificacionOut:
    """Obtiene una certificación y calcula todos los acumulados (Medición anterior, origen, etc.)"""
    # 1. Cargar certificación y sus líneas
    res = await db.execute(
        select(Certificacion)
        .options(selectinload(Certificacion.lineas).selectinload(LineaCertificacion.partida))
        .where(Certificacion.id == certificacion_id)
    )
    cert = res.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificación no encontrada")

    # 2. Cargar todas las certificaciones previas para calcular "Medición Anterior"
    res_previas = await db.execute(
        select(LineaCertificacion.partida_id, func.sum(LineaCertificacion.cantidad_actual))
        .join(Certificacion, LineaCertificacion.certificacion_id == Certificacion.id)
        .where(
            Certificacion.presupuesto_id == cert.presupuesto_id,
            Certificacion.numero < cert.numero,
            Certificacion.estado != EstadoCertificacion.ANULADA
        )
        .group_by(LineaCertificacion.partida_id)
    )
    cantidades_anteriores = {row[0]: row[1] for row in res_previas.all()}

    # 3. Mapear líneas a LineaCertificacionOut
    lineas_out = []
    importe_actual_total = 0.0
    importe_origen_total = 0.0
    presupuesto_total = 0.0

    # Para el presupuesto_total, sumamos todas las partidas del presupuesto original
    res_presup = await db.execute(
        select(Presupuesto)
        .options(selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas))
        .where(Presupuesto.id == cert.presupuesto_id)
    )
    presup = res_presup.scalar_one()
    for cap in presup.capitulos:
        for p in cap.partidas:
            presupuesto_total += float(p.cantidad or 0) * float(p.precio_unitario or 0)

    for linea in cert.lineas:
        partida = linea.partida
        cant_ant = float(cantidades_anteriores.get(partida.id, 0.0))
        cant_origen = cant_ant + float(linea.cantidad_actual or 0)
        
        precio = float(partida.precio_unitario or 0)
        
        imp_act = float(linea.cantidad_actual or 0) * precio
        imp_origen = cant_origen * precio

        cant_partida = float(partida.cantidad or 0)
        porc_avance = (cant_origen / cant_partida * 100) if cant_partida > 0 else 0.0

        importe_actual_total += imp_act
        importe_origen_total += imp_origen

        lineas_out.append(LineaCertificacionOut(
            id=linea.id,
            certificacion_id=linea.certificacion_id,
            partida_id=partida.id,
            cantidad_actual=linea.cantidad_actual,
            codigo_partida=partida.codigo,
            descripcion_partida=partida.descripcion,
            unidad_partida=partida.unidad,
            precio_unitario=partida.precio_unitario,
            cantidad_presupuesto=partida.cantidad,
            cantidad_anterior=cant_ant,
            cantidad_origen=cant_origen,
            porcentaje_avance=porc_avance,
            importe_actual=imp_act,
            importe_origen=imp_origen
        ))

    # Ordenar lineas (opcional)
    lineas_out.sort(key=lambda x: x.codigo_partida)

    avance_total = (importe_origen_total / presupuesto_total * 100) if presupuesto_total > 0 else 0.0

    return CertificacionOut(
        id=cert.id,
        presupuesto_id=cert.presupuesto_id,
        numero=cert.numero,
        fecha=cert.fecha,
        estado=cert.estado,
        observaciones=cert.observaciones,
        created_at=cert.created_at,
        updated_at=cert.updated_at,
        importe_actual=importe_actual_total,
        importe_origen=importe_origen_total,
        presupuesto_total=presupuesto_total,
        porcentaje_avance_total=avance_total,
        lineas=lineas_out
    )

async def crear_certificacion(db: AsyncSession, presupuesto_id: int, data: CertificacionCreate) -> CertificacionOut:
    # Obtener el presupuesto
    res = await db.execute(
        select(Presupuesto)
        .options(selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas))
        .where(Presupuesto.id == presupuesto_id)
    )
    presupuesto = res.scalar_one_or_none()
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    # Obtener último número de certificación
    res_num = await db.execute(
        select(func.max(Certificacion.numero))
        .where(Certificacion.presupuesto_id == presupuesto_id)
    )
    ultimo_numero = res_num.scalar() or 0
    nuevo_numero = ultimo_numero + 1

    certificacion = Certificacion(
        presupuesto_id=presupuesto_id,
        numero=nuevo_numero,
        fecha=data.fecha,
        estado=EstadoCertificacion.BORRADOR,
        observaciones=data.observaciones
    )
    db.add(certificacion)
    await db.flush()

    # Crear una línea en cero para cada partida del presupuesto
    for capitulo in presupuesto.capitulos:
        for partida in capitulo.partidas:
            linea = LineaCertificacion(
                certificacion_id=certificacion.id,
                partida_id=partida.id,
                cantidad_actual=0.0
            )
            db.add(linea)

    await db.commit()
    return await get_certificacion_con_detalles(db, certificacion.id)


async def guardar_mediciones(db: AsyncSession, certificacion_id: int, lineas: List[LineaCertificacionUpdate]) -> CertificacionOut:
    cert = await db.get(Certificacion, certificacion_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificación no encontrada")
    
    if cert.estado != EstadoCertificacion.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden editar certificaciones en estado Borrador")

    # Mapear ids que llegan a actualizar
    updates = {l.partida_id: l.cantidad_actual for l in lineas}

    # Cargar líneas existentes
    res_lineas = await db.execute(
        select(LineaCertificacion).where(LineaCertificacion.certificacion_id == certificacion_id)
    )
    lineas_db = res_lineas.scalars().all()

    for linea in lineas_db:
        if linea.partida_id in updates:
            linea.cantidad_actual = updates[linea.partida_id]

    await db.commit()
    return await get_certificacion_con_detalles(db, certificacion_id)

async def cambiar_estado(db: AsyncSession, certificacion_id: int, estado: EstadoCertificacion) -> CertificacionOut:
    cert = await db.get(Certificacion, certificacion_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificación no encontrada")
        
    cert.estado = estado
    await db.commit()
    return await get_certificacion_con_detalles(db, certificacion_id)
