from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.obra import EstadoObra


class ObraCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    cliente: str | None = Field(default=None, max_length=200)
    direccion: str | None = Field(default=None, max_length=300)


class ObraOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    cliente: str | None
    direccion: str | None
    estado: EstadoObra
    fecha_inicio: date | None
    superficie_m2: float | None
    progreso_porcentaje: int | None
    estado_actual_texto: str | None
    created_at: datetime
    updated_at: datetime

    # Calculados aparte (no son columnas de Obra) — ver routers/obras.py.
    total_visitas: int = 0
    ultima_visita_fecha: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ObraEstadoUpdate(BaseModel):
    estado: EstadoObra


class ObraDetalleUpdate(BaseModel):
    """Campos editables de la ficha de obra (progreso visual, no el estado formal)."""
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    cliente: str | None = None
    direccion: str | None = None
    fecha_inicio: date | None = None
    superficie_m2: float | None = Field(default=None, ge=0)
    progreso_porcentaje: int | None = Field(default=None, ge=0, le=100)
    estado_actual_texto: str | None = Field(default=None, max_length=200)
