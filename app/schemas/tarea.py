from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from app.models.tarea import EstadoTarea
from app.schemas.usuario import UsuarioOut


class TareaBase(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha_limite: Optional[date] = None
    responsable_id: Optional[int] = None
    estado: Optional[EstadoTarea] = EstadoTarea.PENDIENTE


class TareaCreate(TareaBase):
    visita_id: Optional[int] = None


class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_limite: Optional[date] = None
    responsable_id: Optional[int] = None
    estado: Optional[EstadoTarea] = None


class HistorialTareaResponse(BaseModel):
    id: int
    tarea_id: int
    usuario_id: int
    estado_anterior: Optional[EstadoTarea] = None
    estado_nuevo: EstadoTarea
    fecha: datetime
    
    usuario: UsuarioOut

    model_config = ConfigDict(from_attributes=True)


from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.services.storage_service import url_publica

class TareaArchivoResponse(BaseModel):
    id: int
    tipo: str
    nombre_original: str
    url: str | None = None
    ruta_archivo: str = Field(exclude=True, repr=False)

    @model_validator(mode="after")
    def compute_url(self) -> "TareaArchivoResponse":
        if self.ruta_archivo:
            self.url = url_publica(self.ruta_archivo)
        return self

    model_config = ConfigDict(from_attributes=True)


class TareaResponse(TareaBase):
    id: int
    obra_id: int
    visita_id: Optional[int] = None
    creador_id: int
    created_at: datetime
    updated_at: datetime

    responsable: Optional[UsuarioOut] = None
    creador: UsuarioOut
    historial: list[HistorialTareaResponse] = []
    archivos: list[TareaArchivoResponse] = []

    model_config = ConfigDict(from_attributes=True)
