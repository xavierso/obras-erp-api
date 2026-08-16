from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.visita import TipoArchivoVisita


class VisitaArchivoOut(BaseModel):
    id: int
    tipo: TipoArchivoVisita
    nombre_original: str
    url: str

    model_config = ConfigDict(from_attributes=True)


class VisitaOut(BaseModel):
    id: int
    obra_id: int
    descripcion: str | None
    fecha: datetime
    archivos: list[VisitaArchivoOut] = []

    model_config = ConfigDict(from_attributes=True)


class VisitaConObraOut(VisitaOut):
    """Para la vista global de visitas (todas las obras), que necesita
    mostrar a qué obra pertenece cada una."""
    obra_nombre: str
    obra_codigo: str
