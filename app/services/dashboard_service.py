"""
Agregación de estadísticas para el dashboard de la app, equivalente a
las tarjetas "RESUMEN GENERAL" del diseño (obras activas, visitas hoy,
visitas de la semana, documentos nuevos).
"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documento import Documento
from app.models.obra import EstadoObra, Obra
from app.models.visita import Visita

ESTADOS_NO_ACTIVOS = {EstadoObra.ENTREGADA, EstadoObra.ARCHIVADA}


async def obtener_resumen_dashboard(usuario_id: int, db: AsyncSession) -> dict:
    ahora = datetime.now(timezone.utc)
    inicio_hoy = datetime.combine(ahora.date(), time.min, tzinfo=timezone.utc)
    fin_hoy = inicio_hoy + timedelta(days=1)
    inicio_semana = inicio_hoy - timedelta(days=ahora.weekday())  # lunes de esta semana

    # Obras activas: todas las del usuario salvo entregadas/archivadas.
    result = await db.execute(
        select(func.count())
        .select_from(Obra)
        .where(Obra.usuario_id == usuario_id, Obra.estado.notin_(ESTADOS_NO_ACTIVOS))
    )
    obras_activas = result.scalar_one()

    # Visitas de hoy / de esta semana (unidas por obra, ya que Visita no
    # guarda directamente el usuario propietario de la obra).
    result = await db.execute(
        select(func.count())
        .select_from(Visita)
        .join(Obra, Obra.id == Visita.obra_id)
        .where(
            Obra.usuario_id == usuario_id,
            Visita.fecha >= inicio_hoy,
            Visita.fecha < fin_hoy,
        )
    )
    visitas_hoy = result.scalar_one()

    result = await db.execute(
        select(func.count())
        .select_from(Visita)
        .join(Obra, Obra.id == Visita.obra_id)
        .where(Obra.usuario_id == usuario_id, Visita.fecha >= inicio_semana)
    )
    visitas_semana = result.scalar_one()

    result = await db.execute(
        select(func.count())
        .select_from(Documento)
        .join(Obra, Obra.id == Documento.obra_id)
        .where(Obra.usuario_id == usuario_id, Documento.created_at >= inicio_semana)
    )
    documentos_nuevos_semana = result.scalar_one()

    from app.models.actividad_cronograma import ActividadCronograma, EstadoActividad
    from datetime import date
    hoy = date.today()

    # Actividades retrasadas
    result = await db.execute(
        select(func.count())
        .select_from(ActividadCronograma)
        .join(Obra, Obra.id == ActividadCronograma.obra_id)
        .where(
            Obra.usuario_id == usuario_id,
            Obra.estado.notin_(ESTADOS_NO_ACTIVOS),
            ActividadCronograma.porcentaje_avance < 100,
            ActividadCronograma.estado_base != EstadoActividad.CANCELADA,
            ActividadCronograma.fecha_fin_prevista < hoy
        )
    )
    actividades_retrasadas_total = result.scalar_one()

    # Obras avance
    result = await db.execute(
        select(Obra.id, Obra.nombre, Obra.progreso_porcentaje)
        .where(Obra.usuario_id == usuario_id, Obra.estado.notin_(ESTADOS_NO_ACTIVOS))
    )
    obras = result.all()
    obras_avance = [
        {"id": o.id, "nombre": o.nombre, "progreso_porcentaje": o.progreso_porcentaje or 0}
        for o in obras
    ]

    return {
        "obras_activas": obras_activas,
        "visitas_hoy": visitas_hoy,
        "visitas_semana": visitas_semana,
        "documentos_nuevos_semana": documentos_nuevos_semana,
        "actividades_retrasadas_total": actividades_retrasadas_total,
        "obras_avance": obras_avance,
    }
