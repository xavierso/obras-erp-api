from __future__ import annotations
from pydantic import BaseModel
from typing import Literal


class LineaMedicionIntermedia(BaseModel):
    comentario: str | None = None
    unidades: float | None = None
    longitud: float | None = None
    anchura: float | None = None
    altura: float | None = None
    subtotal: float = 0.0

class PartidaIntermedia(BaseModel):
    codigo: str = ""
    descripcion: str = ""
    unidad: str = "ud"
    cantidad: float = 1.0
    precio_unitario: float = 0.0
    importe: float = 0.0
    descuento_porcentaje: float = 0.0
    status: Literal["ok", "warning", "error"] = "ok"
    warnings: list[str] = []
    fila_origen: int = 0
    lineas_medicion: list[LineaMedicionIntermedia] = []
    observaciones: str | None = None


class CapituloIntermedio(BaseModel):
    codigo: str = ""
    nombre: str = ""
    orden: int = 0
    partidas: list[PartidaIntermedia] = []
    subcapitulos: list[CapituloIntermedio] = []


class MetadatosPresupuesto(BaseModel):
    nombre_obra: str | None = None
    cliente: str | None = None
    direccion: str | None = None
    fecha: str | None = None
    codigo_presupuesto: str | None = None
    observaciones: str | None = None
    iva: float = 21.0


class ColumnMapping(BaseModel):
    codigo: int | None = None
    descripcion: int | None = None
    unidad: int | None = None
    cantidad: int | None = None
    precio_unitario: int | None = None
    descuento: int | None = None
    importe: int | None = None


class ResultadoAnalisis(BaseModel):
    metadatos: MetadatosPresupuesto
    capitulos: list[CapituloIntermedio]
    column_mapping: ColumnMapping
    total_capitulos: int = 0
    total_partidas: int = 0
    partidas_ok: int = 0
    partidas_warning: int = 0
    partidas_error: int = 0
    importe_total_detectado: float = 0.0
    warnings_globales: list[str] = []
    columnas_excel: list[str] = []
