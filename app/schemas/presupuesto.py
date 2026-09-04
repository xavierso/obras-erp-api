from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.presupuesto import EstadoPresupuesto


# LINEAS DE MEDICION
class LineaMedicionBase(BaseModel):
    comentario: Optional[str] = None
    unidades: float = 1
    longitud: Optional[float] = None
    anchura: Optional[float] = None
    altura: Optional[float] = None

class LineaMedicionCreate(LineaMedicionBase):
    pass

class LineaMedicionUpdate(BaseModel):
    comentario: Optional[str] = None
    unidades: Optional[float] = None
    longitud: Optional[float] = None
    anchura: Optional[float] = None
    altura: Optional[float] = None

class LineaMedicionOut(LineaMedicionBase):
    id: int
    partida_id: int
    subtotal: float

    model_config = ConfigDict(from_attributes=True)


# PARTIDAS
class PartidaPresupuestoBase(BaseModel):
    codigo: str
    descripcion: str
    unidad: str
    cantidad: float = 1
    coste_base: Optional[float] = 0
    coste_material: Optional[float] = 0
    porcentaje_indirectos: Optional[float] = 0
    porcentaje_comisiones: Optional[float] = 0
    coste_unitario: Optional[float] = 0
    precio_unitario: float = 0
    descuento_porcentaje: Optional[float] = 0
    margen_porcentaje: Optional[float] = 0
    observaciones: Optional[str] = None

class PartidaPresupuestoCreate(PartidaPresupuestoBase):
    pass

class PartidaPresupuestoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=50)
    descripcion: Optional[str] = None
    unidad: Optional[str] = Field(None, max_length=20)
    cantidad: Optional[float] = None
    coste_base: Optional[float] = None
    coste_material: Optional[float] = None
    porcentaje_indirectos: Optional[float] = None
    porcentaje_comisiones: Optional[float] = None
    coste_unitario: Optional[float] = None
    precio_unitario: Optional[float] = None
    descuento_porcentaje: Optional[float] = None
    margen_porcentaje: Optional[float] = None
    observaciones: Optional[str] = None

class PartidaPresupuestoOut(PartidaPresupuestoBase):
    id: int
    capitulo_id: int
    precio_con_descuento: float
    cantidad_calculada: float
    importe: float
    coste_total: float
    lineas_medicion: List[LineaMedicionOut] = []

    model_config = ConfigDict(from_attributes=True)


# CAPITULOS
class CapituloPresupuestoBase(BaseModel):
    nombre: str = Field(..., max_length=200)
    orden: int = 0
    padre_id: Optional[int] = None

class CapituloPresupuestoCreate(CapituloPresupuestoBase):
    partidas: Optional[List[PartidaPresupuestoCreate]] = []

class CapituloPresupuestoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    orden: Optional[int] = None
    padre_id: Optional[int] = None

class CapituloPresupuestoOut(CapituloPresupuestoBase):
    id: int
    presupuesto_id: int
    subtotal: float
    partidas: List[PartidaPresupuestoOut] = []
    subcapitulos: List['CapituloPresupuestoOut'] = []

    model_config = ConfigDict(from_attributes=True)


# PRESUPUESTO
class PresupuestoBase(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    fecha: Optional[date] = None
    version: Optional[int] = 1
    observaciones: Optional[str] = None
    iva: Optional[float] = 21.0
    estado: Optional[EstadoPresupuesto] = EstadoPresupuesto.BORRADOR
    es_version_activa: Optional[bool] = False
    coste_estimado_obra: Optional[float] = None
    
    codigo: Optional[str] = None
    cliente_nombre: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None

class PresupuestoCreate(PresupuestoBase):
    obra_id: Optional[int] = None
    capitulos: Optional[List[CapituloPresupuestoCreate]] = []

class PresupuestoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    descripcion: Optional[str] = None
    fecha: Optional[date] = None
    observaciones: Optional[str] = None
    iva: Optional[float] = None
    coste_estimado_obra: Optional[float] = None
    obra_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    direccion: Optional[str] = None
    codigo_postal: Optional[str] = None
    # No permitimos cambiar estado, versión o código directamente por aquí

class PresupuestoAprobar(BaseModel):
    # Dto simple para la confirmación. Si no había obra, se pueden pasar datos básicos
    obra_nombre: Optional[str] = None
    obra_direccion: Optional[str] = None

class PresupuestoEstadoUpdate(BaseModel):
    estado: EstadoPresupuesto

class PresupuestoOut(PresupuestoBase):
    id: int
    obra_id: Optional[int] = None
    creador_id: Optional[int] = None
    aprobador_id: Optional[int] = None
    fecha_aprobacion: Optional[datetime] = None
    
    coste_directo: float
    importe_iva: float
    total: float
    
    capitulos: List[CapituloPresupuestoOut] = []
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresupuestoResumenOut(PresupuestoBase):
    """Para listados, sin los capítulos anidados"""
    id: int
    obra_id: Optional[int] = None
    coste_directo: float
    importe_iva: float
    total: float
    
    class Config:
        from_attributes = True


# Generar Cronograma
class GenerarCronogramaItem(BaseModel):
    partida_id: int
    # En el futuro se podrían pedir las fechas aquí, pero por ahora se transfieren solas

class GenerarCronogramaReq(BaseModel):
    partidas: List[GenerarCronogramaItem]
