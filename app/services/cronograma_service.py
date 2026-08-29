from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.actividad_cronograma import ActividadCronograma
from app.models.obra import Obra


async def actualizar_progreso_obra(obra_id: int, db: AsyncSession) -> None:
    """Calcula y actualiza el progreso ponderado de la obra según las actividades."""
    result = await db.execute(select(ActividadCronograma).where(ActividadCronograma.obra_id == obra_id))
    actividades = result.scalars().all()
    
    if not actividades:
        # Si no hay actividades, el progreso es 0 o lo dejamos igual (decidamos 0 por coherencia)
        obra_res = await db.execute(select(Obra).where(Obra.id == obra_id))
        obra = obra_res.scalar_one_or_none()
        if obra:
            obra.progreso_porcentaje = 0
            await db.commit()
        return

    duracion_total = 0
    progreso_ponderado_total = 0.0

    for act in actividades:
        if act.es_hito:
            continue  # Los hitos (1 día o 0 días) normalmente no ponderan para el progreso físico de ejecución

        dias = (act.fecha_fin_prevista - act.fecha_inicio).days
        duracion = max(dias, 0) + 1  # Al menos 1 día de duración
        
        duracion_total += duracion
        progreso_ponderado_total += duracion * (act.porcentaje_avance / 100.0)

    nuevo_progreso = 0
    if duracion_total > 0:
        nuevo_progreso = int(round((progreso_ponderado_total / duracion_total) * 100))

    obra_res = await db.execute(select(Obra).where(Obra.id == obra_id))
    obra = obra_res.scalar_one_or_none()
    if obra:
        obra.progreso_porcentaje = nuevo_progreso
        await db.commit()
