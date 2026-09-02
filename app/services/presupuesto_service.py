from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.presupuesto import Presupuesto, CapituloPresupuesto, PartidaPresupuesto, EstadoPresupuesto
from app.models.obra import Obra
from app.models.actividad_cronograma import ActividadCronograma
from app.schemas.presupuesto import PresupuestoCreate, PresupuestoUpdate, CapituloPresupuestoCreate, PartidaPresupuestoCreate


async def get_presupuesto(db: AsyncSession, presupuesto_id: int, empresa_id: int = None) -> Optional[Presupuesto]:
    stmt = select(Presupuesto).options(
        selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas),
        selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.subcapitulos)
    ).where(Presupuesto.id == presupuesto_id)
    
    if empresa_id is not None:
        stmt = stmt.where(Presupuesto.empresa_id == empresa_id)
        
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def crear_presupuesto(db: AsyncSession, data: PresupuestoCreate, creador_id: int, empresa_id: int = None) -> Presupuesto:
    # Check if Obra exists if obra_id is provided
    if data.obra_id:
        obra = await db.get(Obra, data.obra_id)
        if not obra:
            raise HTTPException(status_code=404, detail="Obra no encontrada")
        
    # Generar código PTO-YYYY-XXX
    from sqlalchemy import select, desc
    from datetime import datetime, timezone
    
    año_actual = datetime.now(timezone.utc).year
    prefijo = f"PTO-{año_actual}-"
    
    result = await db.execute(
        select(Presupuesto.codigo)
        .where(Presupuesto.codigo.like(f"{prefijo}%"))
        .order_by(desc(Presupuesto.codigo))
        .limit(1)
    )
    ultimo_codigo = result.scalar_one_or_none()
    
    if ultimo_codigo:
        try:
            ultimo_numero = int(ultimo_codigo.split("-")[-1])
            nuevo_numero = ultimo_numero + 1
        except ValueError:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
        
    codigo_generado = f"{prefijo}{nuevo_numero:03d}"

    presupuesto = Presupuesto(
        codigo=codigo_generado,
        nombre=data.nombre,
        descripcion=data.descripcion,
        fecha=data.fecha,
        version=data.version or 1,
        observaciones=data.observaciones,
        iva=data.iva,
        estado=EstadoPresupuesto.BORRADOR,
        es_version_activa=data.es_version_activa,
        coste_estimado_obra=data.coste_estimado_obra,
        obra_id=data.obra_id,
        creador_id=creador_id,
        empresa_id=empresa_id,
        cliente_nombre=getattr(data, 'cliente_nombre', None),
        direccion=getattr(data, 'direccion', None),
        codigo_postal=getattr(data, 'codigo_postal', None)
    )
    db.add(presupuesto)
    await db.flush() # Para obtener presupuesto.id

    if data.capitulos:
        for idx, cap_data in enumerate(data.capitulos):
            capitulo = CapituloPresupuesto(
                nombre=cap_data.nombre,
                orden=cap_data.orden or idx,
                padre_id=cap_data.padre_id,
                presupuesto_id=presupuesto.id
            )
            db.add(capitulo)
            await db.flush()

            if cap_data.partidas:
                for part_data in cap_data.partidas:
                    partida = PartidaPresupuesto(
                        codigo=part_data.codigo,
                        descripcion=part_data.descripcion,
                        unidad=part_data.unidad,
                        cantidad=part_data.cantidad,
                        coste_unitario=part_data.coste_unitario,
                        precio_unitario=part_data.precio_unitario,
                        descuento_porcentaje=part_data.descuento_porcentaje,
                        margen_porcentaje=part_data.margen_porcentaje,
                        observaciones=part_data.observaciones,
                        capitulo_id=capitulo.id
                    )
                    db.add(partida)

    await db.commit()
    return await get_presupuesto(db, presupuesto.id)


async def actualizar_presupuesto(db: AsyncSession, presupuesto_id: int, data: PresupuestoUpdate) -> Presupuesto:
    presupuesto = await get_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(presupuesto, key, value)
        
    await db.commit()
    return await get_presupuesto(db, presupuesto_id)


async def aprobar_presupuesto(db: AsyncSession, presupuesto_id: int, aprobador_id: int, datos_obra: dict = None) -> Presupuesto:
    presupuesto = await get_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
    if not presupuesto.capitulos:
        raise HTTPException(status_code=400, detail="No se puede aprobar un presupuesto sin capítulos")
        
    tiene_partidas = any(len(c.partidas) > 0 for c in presupuesto.capitulos)
    if not tiene_partidas:
        raise HTTPException(status_code=400, detail="No se puede aprobar un presupuesto sin partidas")

    # Si no tiene obra, creamos una
    if not presupuesto.obra_id:
        from app.models.obra import EstadoObra
        from datetime import date
        
        # Generar código (simplificado)
        count_res = await db.execute(select(Obra))
        count = len(count_res.scalars().all()) + 1
        nuevo_codigo = f"OB-{date.today().year}-{count:03d}"
        
        nueva_obra = Obra(
            codigo=nuevo_codigo,
            nombre=datos_obra.get('obra_nombre') if datos_obra and datos_obra.get('obra_nombre') else f"Obra de: {presupuesto.nombre}",
            direccion=datos_obra.get('obra_direccion') if datos_obra else None,
            estado=EstadoObra.PENDIENTE,
            usuario_id=aprobador_id
        )
        db.add(nueva_obra)
        await db.flush()
        presupuesto.obra_id = nueva_obra.id
    else:
        # Desactivar otras versiones activas si ya hay obra
        await db.execute(
            select(Presupuesto)
            .where(Presupuesto.obra_id == presupuesto.obra_id, Presupuesto.es_version_activa == True)
        )

    # Marcar como activa y aprobar
    presupuesto.estado = EstadoPresupuesto.APROBADO
    presupuesto.es_version_activa = True
    presupuesto.aprobador_id = aprobador_id
    presupuesto.fecha_aprobacion = datetime.now(timezone.utc)
    
    await db.commit()
    return await get_presupuesto(db, presupuesto_id)


async def cambiar_estado_presupuesto(db: AsyncSession, presupuesto_id: int, nuevo_estado: EstadoPresupuesto):
    # Simple SELECT without loading relations
    result = await db.execute(
        select(Presupuesto).where(Presupuesto.id == presupuesto_id)
    )
    presupuesto = result.scalar_one_or_none()
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    presupuesto.estado = nuevo_estado
    
    # Handle cancellation
    if nuevo_estado == EstadoPresupuesto.CANCELADO:
        presupuesto.es_version_activa = False
    
    await db.commit()
    return {"id": presupuesto_id, "estado": nuevo_estado.value}


async def generar_cronograma_desde_presupuesto(db: AsyncSession, presupuesto_id: int, partidas_ids: List[int], usuario_id: int):
    presupuesto = await get_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
    if presupuesto.estado not in (EstadoPresupuesto.APROBADO, EstadoPresupuesto.EN_EJECUCION):
        raise HTTPException(status_code=400, detail="El presupuesto debe estar aprobado o en ejecución")
        
    partidas_creadas = 0
    from datetime import date
    
    # Recorrer capítulos para mantener orden y buscar partidas
    for capitulo in presupuesto.capitulos:
        for partida in capitulo.partidas:
            if partida.id in partidas_ids:
                # Comprobar si ya existe una actividad para esta partida
                res = await db.execute(
                    select(ActividadCronograma)
                    .where(ActividadCronograma.partida_presupuesto_id == partida.id)
                )
                if res.scalar_one_or_none():
                    continue # Ya existe
                    
                # Crear actividad
                actividad = ActividadCronograma(
                    nombre=f"[{partida.codigo}] {partida.descripcion}",
                    obra_id=presupuesto.obra_id,
                    partida_presupuesto_id=partida.id,
                    fecha_inicio=date.today(), # Por defecto, el usuario la cambiará después
                    fecha_fin_prevista=date.today(), 
                    porcentaje_avance=0,
                    responsable_id=usuario_id,
                    observaciones=f"Importado de presupuesto {presupuesto.nombre}"
                )
                db.add(actividad)
                partidas_creadas += 1

    if partidas_creadas > 0:
        if presupuesto.estado == EstadoPresupuesto.APROBADO:
            presupuesto.estado = EstadoPresupuesto.EN_EJECUCION
        await db.commit()
        
    return {"message": f"Se han generado {partidas_creadas} actividades en el cronograma"}


from sqlalchemy.orm import selectinload

async def crear_capitulo(db: AsyncSession, presupuesto_id: int, data: CapituloPresupuestoCreate) -> CapituloPresupuesto:
    capitulo = CapituloPresupuesto(
        nombre=data.nombre,
        orden=data.orden,
        padre_id=data.padre_id,
        presupuesto_id=presupuesto_id
    )
    db.add(capitulo)
    await db.commit()
    stmt = select(CapituloPresupuesto).options(
        selectinload(CapituloPresupuesto.partidas),
        selectinload(CapituloPresupuesto.subcapitulos)
    ).where(CapituloPresupuesto.id == capitulo.id)
    result = await db.execute(stmt)
    return result.scalar_one()

async def eliminar_capitulo(db: AsyncSession, capitulo_id: int):
    capitulo = await db.get(CapituloPresupuesto, capitulo_id)
    if not capitulo:
        raise HTTPException(status_code=404, detail="Capítulo no encontrado")
    await db.delete(capitulo)
    await db.commit()
    return {"message": "Capítulo eliminado"}

async def crear_partida(db: AsyncSession, capitulo_id: int, data: PartidaPresupuestoCreate) -> PartidaPresupuesto:
    partida = PartidaPresupuesto(
        codigo=data.codigo,
        descripcion=data.descripcion,
        unidad=data.unidad,
        cantidad=data.cantidad,
        coste_base=data.coste_base,
        coste_material=data.coste_material,
        porcentaje_indirectos=data.porcentaje_indirectos,
        porcentaje_comisiones=data.porcentaje_comisiones,
        coste_unitario=data.coste_unitario,
        precio_unitario=data.precio_unitario,
        descuento_porcentaje=data.descuento_porcentaje,
        margen_porcentaje=data.margen_porcentaje,
        observaciones=data.observaciones,
        capitulo_id=capitulo_id
    )
    db.add(partida)
    await db.commit()
    await db.refresh(partida)
    return partida

async def eliminar_partida(db: AsyncSession, partida_id: int):
    partida = await db.get(PartidaPresupuesto, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    await db.delete(partida)
    await db.commit()
    return {"message": "Partida eliminada"}

from app.schemas.presupuesto import PartidaPresupuestoUpdate

async def actualizar_partida(db: AsyncSession, partida_id: int, data: PartidaPresupuestoUpdate) -> PartidaPresupuesto:
    partida = await db.get(PartidaPresupuesto, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(partida, key, value)
        
    await db.commit()
    await db.refresh(partida)
    return partida
