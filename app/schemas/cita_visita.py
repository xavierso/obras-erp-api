from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.cita_visita import EstadoCita

# Atajos habituales del bot: sin recordatorio, 30 min, 3 horas, 1 día antes.
RECORDATORIOS_PERMITIDOS = {None, 0, 30, 180, 1440}


class CitaVisitaCreate(BaseModel):
    obra_id: int | None = None
    nombre_referencia: str | None = Field(default=None, max_length=200)
    fecha_hora: datetime
    notas: str | None = None
    recordatorio_minutos_antes: int | None = None

    @model_validator(mode="after")
    def _validar_referencia(self):
        if self.obra_id is None and not self.nombre_referencia:
            raise ValueError(
                "Debes indicar obra_id (obra formal) o nombre_referencia "
                "(visita potencial/presupuesto)"
            )
        return self


class CitaVisitaUpdate(BaseModel):
    """Para reprogramar: fecha, notas o recordatorio. Todo opcional."""
    fecha_hora: datetime | None = None
    notas: str | None = None
    recordatorio_minutos_antes: int | None = None


class CitaVisitaEstadoUpdate(BaseModel):
    estado: EstadoCita


class CitaVisitaOut(BaseModel):
    id: int
    obra_id: int | None
    nombre_referencia: str | None
    fecha_hora: datetime
    notas: str | None
    estado: EstadoCita
    recordatorio_minutos_antes: int | None
    recordatorio_enviado: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
