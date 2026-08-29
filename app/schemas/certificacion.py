from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.certificacion import EstadoCertificacion

# --- LÍNEAS DE CERTIFICACIÓN ---

class LineaCertificacionBase(BaseModel):
    cantidad_actual: float = 0.0

class LineaCertificacionUpdate(LineaCertificacionBase):
    partida_id: int

class LineaCertificacionOut(LineaCertificacionBase):
    id: int
    certificacion_id: int
    partida_id: int

    # Campos que vendrán cruzados o calculados al devolver el detalle
    codigo_partida: str = ""
    descripcion_partida: str = ""
    unidad_partida: str = ""
    precio_unitario: float = 0.0
    cantidad_presupuesto: float = 0.0
    cantidad_anterior: float = 0.0
    cantidad_origen: float = 0.0
    porcentaje_avance: float = 0.0
    importe_actual: float = 0.0
    importe_origen: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# --- CERTIFICACIÓN ---

class CertificacionBase(BaseModel):
    fecha: date
    estado: Optional[EstadoCertificacion] = EstadoCertificacion.BORRADOR
    observaciones: Optional[str] = None

class CertificacionCreate(CertificacionBase):
    pass

class CertificacionUpdate(BaseModel):
    fecha: Optional[date] = None
    estado: Optional[EstadoCertificacion] = None
    observaciones: Optional[str] = None

class CertificacionEstadoUpdate(BaseModel):
    estado: EstadoCertificacion

class CertificacionOut(CertificacionBase):
    id: int
    presupuesto_id: int
    numero: int
    
    # Totales calculados en el backend
    importe_actual: float = 0.0
    importe_origen: float = 0.0
    presupuesto_total: float = 0.0
    porcentaje_avance_total: float = 0.0

    lineas: List[LineaCertificacionOut] = []

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CertificacionResumenOut(CertificacionBase):
    id: int
    presupuesto_id: int
    numero: int
    importe_actual: float = 0.0
    porcentaje_avance_total: float = 0.0

    model_config = ConfigDict(from_attributes=True)
