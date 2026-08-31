from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.actividad_cronograma import EstadoActividad


class ActividadCronogramaBase(BaseModel):
    nombre: str = Field(..., max_length=200)
    fecha_inicio: date
    fecha_fin_prevista: date
    fecha_fin_real: Optional[date] = None
    porcentaje_avance: int = Field(default=0, ge=0, le=100)
    estado_base: EstadoActividad = EstadoActividad.NO_INICIADA
    responsable_id: Optional[int] = None
    prioridad: Optional[str] = Field(default=None, max_length=50)
    observaciones: Optional[str] = Field(default=None, max_length=500)
    es_hito: bool = False


class ActividadCronogramaCreate(ActividadCronogramaBase):
    obra_id: int
    predecesoras_ids: Optional[list[int]] = Field(default_factory=list)


class ActividadCronogramaUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=200)
    fecha_inicio: Optional[date] = None
    fecha_fin_prevista: Optional[date] = None
    fecha_fin_real: Optional[date] = None
    porcentaje_avance: Optional[int] = Field(default=None, ge=0, le=100)
    estado_base: Optional[EstadoActividad] = None
    responsable_id: Optional[int] = None
    prioridad: Optional[str] = Field(default=None, max_length=50)
    observaciones: Optional[str] = Field(default=None, max_length=500)
    es_hito: Optional[bool] = None
    predecesoras_ids: Optional[list[int]] = None


class ActividadCronogramaResponse(ActividadCronogramaBase):
    id: int
    obra_id: int
    estado: EstadoActividad  # Este es el estado dinámico
    created_at: datetime
    updated_at: datetime
    predecesoras_ids: list[int] = []

    class Config:
        from_attributes = True
