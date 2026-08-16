from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.visita import TipoArchivoVisita


class VisitaPotencialArchivoOut(BaseModel):
    id: int
    tipo: TipoArchivoVisita
    nombre_original: str
    url: str

    model_config = ConfigDict(from_attributes=True)


class VisitaPotencialOut(BaseModel):
    id: int
    cita_id: int
    descripcion: str | None
    fecha: datetime
    archivos: list[VisitaPotencialArchivoOut] = []

    model_config = ConfigDict(from_attributes=True)
