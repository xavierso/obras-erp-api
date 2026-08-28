from datetime import date, time, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user, get_empresa_id
from app.models.usuario import Usuario, RolUsuario
from app.models.obra import Obra
from app.models.visita import Visita
from app.models.tarea import Tarea, EstadoTarea
from app.models.incidencia import Incidencia, EstadoIncidencia
from app.models.cita_visita import CitaVisita, EstadoCita
from app.models.evento_calendario import EventoCalendario, TipoEventoCalendario, EstadoEventoCalendario
from app.schemas.calendario import EventoCalendarioOut, EventoCustomCreate, EventoCustomOut

router = APIRouter(prefix="/calendario", tags=["Calendario"])

@router.get("/eventos", response_model=List[EventoCalendarioOut])
async def obtener_eventos_calendario(
    obra_id: Optional[int] = None,
    responsable_id: Optional[int] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    tipos: Optional[List[str]] = Query(None),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Motor Temporal: recupera todos los eventos relevantes para el calendario.
    Filtra las obras accesibles según la empresa del usuario.
    Si obra_id es nulo, devuelve los de todas las obras de la empresa.
    Si responsable_id está presente, filtra por usuario (Mi Agenda).
    """
    eventos: List[EventoCalendarioOut] = []

    # Permisos: El usuario puede ver las obras de su empresa.
    res = await db.execute(select(Obra.id).where(Obra.usuario_id == empresa_id))
    obras_accesibles = [r[0] for r in res.all()]
    if not obras_accesibles:
        return []
    
    # 1. TAREAS
    if not tipos or "tarea" in tipos:
        q_tareas = select(Tarea).options(selectinload(Tarea.obra)).join(Obra, isouter=True)
        if obra_id:
            q_tareas = q_tareas.where(Tarea.obra_id == obra_id)
        elif obras_accesibles is not None:
            q_tareas = q_tareas.where(Tarea.obra_id.in_(obras_accesibles))
        
        if responsable_id:
            q_tareas = q_tareas.where(Tarea.responsable_id == responsable_id)
        
        if fecha_inicio:
            q_tareas = q_tareas.where(Tarea.fecha_limite >= fecha_inicio)
        if fecha_fin:
            q_tareas = q_tareas.where(Tarea.fecha_limite <= fecha_fin)

        res_tareas = await db.execute(q_tareas)
        tareas = res_tareas.scalars().all()
        for t in tareas:
            if t.fecha_limite:
                eventos.append(EventoCalendarioOut(
                    id=f"tarea-{t.id}",
                    tipo="tarea",
                    titulo=t.titulo,
                    descripcion=t.descripcion,
                    obra_id=t.obra_id,
                    obra_nombre=t.obra.nombre if t.obra else None,
                    responsable_id=t.responsable_id,
                    responsable_nombre=None, # Idealmente precargar responsable
                    fecha=t.fecha_limite,
                    estado=t.estado
                ))

    # 2. INCIDENCIAS
    if not tipos or "incidencia" in tipos:
        q_incid = select(Incidencia).options(selectinload(Incidencia.obra)).join(Obra, isouter=True)
        if obra_id:
            q_incid = q_incid.where(Incidencia.obra_id == obra_id)
        elif obras_accesibles is not None:
            q_incid = q_incid.where(Incidencia.obra_id.in_(obras_accesibles))
            
        if responsable_id:
            q_incid = q_incid.where(Incidencia.responsable_id == responsable_id)
            
        if fecha_inicio:
            q_incid = q_incid.where(or_(Incidencia.fecha_limite >= fecha_inicio, Incidencia.fecha_deteccion >= fecha_inicio))
        if fecha_fin:
            q_incid = q_incid.where(or_(Incidencia.fecha_limite <= fecha_fin, Incidencia.fecha_deteccion <= fecha_fin))

        res_incid = await db.execute(q_incid)
        incidencias = res_incid.scalars().all()
        for i in incidencias:
            fecha_evento = i.fecha_limite if i.fecha_limite else i.fecha_deteccion
            eventos.append(EventoCalendarioOut(
                id=f"incidencia-{i.id}",
                tipo="incidencia",
                titulo=f"{i.codigo} - {i.titulo}",
                descripcion=i.descripcion,
                obra_id=i.obra_id,
                obra_nombre=i.obra.nombre if i.obra else None,
                responsable_id=i.responsable_id,
                fecha=fecha_evento,
                estado=i.estado
            ))

    # 3. VISITAS
    if not tipos or "visita" in tipos:
        q_visitas = select(Visita).options(selectinload(Visita.obra)).join(Obra, isouter=True)
        if obra_id:
            q_visitas = q_visitas.where(Visita.obra_id == obra_id)
        elif obras_accesibles is not None:
            q_visitas = q_visitas.where(Visita.obra_id.in_(obras_accesibles))
            
        if responsable_id:
            q_visitas = q_visitas.where(Visita.usuario_id == responsable_id)
            
        if fecha_inicio:
            q_visitas = q_visitas.where(Visita.fecha >= fecha_inicio)
        if fecha_fin:
            q_visitas = q_visitas.where(Visita.fecha <= fecha_fin)

        res_vis = await db.execute(q_visitas)
        visitas = res_vis.scalars().all()
        for v in visitas:
            eventos.append(EventoCalendarioOut(
                id=f"visita-{v.id}",
                tipo="visita",
                titulo=f"Visita - {v.obra.nombre if v.obra else 'Obra'}",
                descripcion=v.descripcion,
                obra_id=v.obra_id,
                obra_nombre=v.obra.nombre if v.obra else None,
                responsable_id=v.usuario_id,
                fecha=v.fecha.date() if isinstance(v.fecha, datetime) else v.fecha,
                estado="completada" # Las visitas en la tabla Visita ya están realizadas
            ))

    # 4. CITAS / REUNIONES PROGRAMADAS
    if not tipos or "reunion" in tipos:
        q_citas = select(CitaVisita).options(selectinload(CitaVisita.obra)).join(Obra, isouter=True)
        if obra_id:
            q_citas = q_citas.where(CitaVisita.obra_id == obra_id)
        elif obras_accesibles is not None:
            q_citas = q_citas.where(CitaVisita.obra_id.in_(obras_accesibles))
            
        if responsable_id:
            q_citas = q_citas.where(CitaVisita.usuario_id == responsable_id)
            
        if fecha_inicio:
            q_citas = q_citas.where(CitaVisita.fecha_hora >= datetime.combine(fecha_inicio, time.min).replace(tzinfo=timezone.utc))
        if fecha_fin:
            q_citas = q_citas.where(CitaVisita.fecha_hora <= datetime.combine(fecha_fin, time.max).replace(tzinfo=timezone.utc))

        res_cit = await db.execute(q_citas)
        citas = res_cit.scalars().all()
        for c in citas:
            eventos.append(EventoCalendarioOut(
                id=f"cita-{c.id}",
                tipo="reunion",
                titulo=f"Cita/Reunión - {c.obra.nombre if c.obra else c.nombre_referencia}",
                descripcion=c.notas,
                obra_id=c.obra_id,
                obra_nombre=c.obra.nombre if c.obra else c.nombre_referencia,
                responsable_id=c.usuario_id,
                fecha=c.fecha_hora.date(),
                hora_inicio=c.fecha_hora.time(),
                estado=c.estado
            ))

    # 5. EVENTOS CUSTOM (Hitos, Entregas, etc.)
    q_custom = select(EventoCalendario).options(selectinload(EventoCalendario.obra)).join(Obra, isouter=True)
    if obra_id:
        q_custom = q_custom.where(EventoCalendario.obra_id == obra_id)
    elif obras_accesibles is not None:
        q_custom = q_custom.where(EventoCalendario.obra_id.in_(obras_accesibles))
        
    if responsable_id:
        q_custom = q_custom.where(EventoCalendario.responsable_id == responsable_id)
        
    if fecha_inicio:
        q_custom = q_custom.where(EventoCalendario.fecha >= fecha_inicio)
    if fecha_fin:
        q_custom = q_custom.where(EventoCalendario.fecha <= fecha_fin)

    res_cust = await db.execute(q_custom)
    eventos_custom = res_cust.scalars().all()
    for ev in eventos_custom:
        if not tipos or ev.tipo.value in tipos:
            eventos.append(EventoCalendarioOut(
                id=f"custom-{ev.id}",
                tipo=ev.tipo.value,
                titulo=ev.titulo,
                descripcion=ev.descripcion,
                obra_id=ev.obra_id,
                obra_nombre=ev.obra.nombre if ev.obra else None,
                responsable_id=ev.responsable_id,
                fecha=ev.fecha,
                hora_inicio=ev.hora_inicio,
                hora_fin=ev.hora_fin,
                estado=ev.estado
            ))

    # Ordenar por fecha
    eventos.sort(key=lambda x: (x.fecha, x.hora_inicio or time.min))
    return eventos

@router.post("/eventos", response_model=EventoCustomOut)
async def crear_evento_custom(
    evento: EventoCustomCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    nuevo = EventoCalendario(
        tipo=TipoEventoCalendario(evento.tipo),
        titulo=evento.titulo,
        descripcion=evento.descripcion,
        obra_id=evento.obra_id,
        responsable_id=evento.responsable_id,
        creador_id=usuario_actual.id,
        fecha=evento.fecha,
        hora_inicio=evento.hora_inicio,
        hora_fin=evento.hora_fin
    )
    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return nuevo
