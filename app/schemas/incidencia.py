from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.incidencia import EstadoIncidencia
from app.schemas.usuario import UsuarioOut
from app.services.storage_service import url_publica


class IncidenciaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_deteccion: date
    fecha_limite: Optional[date] = None
    estado: EstadoIncidencia = EstadoIncidencia.NUEVA


class IncidenciaCreate(IncidenciaBase):
    visita_id: Optional[int] = None
    actividad_id: Optional[int] = None
    responsable_id: Optional[int] = None


class IncidenciaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_deteccion: Optional[date] = None
    fecha_limite: Optional[date] = None
    responsable_id: Optional[int] = None
    actividad_id: Optional[int] = None
    estado: Optional[EstadoIncidencia] = None


class HistorialIncidenciaResponse(BaseModel):
    id: int
    estado_anterior: Optional[EstadoIncidencia]
    estado_nuevo: EstadoIncidencia
    fecha: datetime
    usuario: UsuarioOut

    model_config = ConfigDict(from_attributes=True)


class IncidenciaArchivoResponse(BaseModel):
    id: int
    tipo: str
    nombre_original: str
    url: str | None = None
    ruta_archivo: str = Field(exclude=True, repr=False)

    @model_validator(mode="after")
    def compute_url(self) -> "IncidenciaArchivoResponse":
        if self.ruta_archivo:
            self.url = url_publica(self.ruta_archivo)
        return self

    model_config = ConfigDict(from_attributes=True)


class IncidenciaResponse(IncidenciaBase):
    id: int
    codigo: str
    obra_id: int
    visita_id: Optional[int] = None
    actividad_id: Optional[int] = None
    creador_id: int
    responsable_id: Optional[int] = None
    fecha_resolucion: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    responsable: Optional[UsuarioOut] = None
    creador: UsuarioOut
    historial: list[HistorialIncidenciaResponse] = []
    archivos: list[IncidenciaArchivoResponse] = []
    tareas: list = [] # Se tipifica con list normal para no crear circular imports con TareaResponse, FastAPI lo maneja.

    model_config = ConfigDict(from_attributes=True)
