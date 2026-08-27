from datetime import date, time, datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field

# Esquemas para crear un evento custom
class EventoCustomCreate(BaseModel):
    tipo: Literal["hito", "reunion", "entrega", "otro"]
    titulo: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    obra_id: Optional[int] = None
    responsable_id: Optional[int] = None
    fecha: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None

class EventoCustomOut(BaseModel):
    id: int
    tipo: str
    titulo: str
    descripcion: Optional[str]
    obra_id: Optional[int]
    responsable_id: Optional[int]
    creador_id: int
    fecha: date
    hora_inicio: Optional[time]
    hora_fin: Optional[time]
    estado: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Esquema unificado para devolver eventos al frontend (Visitas, Tareas, Incidencias, EventosCustom)
class EventoCalendarioOut(BaseModel):
    id: str  # e.g., "visita-1", "tarea-2", "custom-3", "cita-4"
    tipo: str  # visita, tarea, incidencia, hito, reunion, entrega, otro
    titulo: str
    descripcion: Optional[str] = None
    obra_id: Optional[int] = None
    obra_nombre: Optional[str] = None
    responsable_id: Optional[int] = None
    responsable_nombre: Optional[str] = None
    fecha: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    estado: Optional[str] = None

    class Config:
        from_attributes = True
