from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PerfilEmpresaUpdate(BaseModel):
    nombre_empresa: str = Field(min_length=2, max_length=200)
    color_principal: str = Field(
        default="#1E3A5F",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color de marca en formato hexadecimal, ej. #1E3A5F",
    )
    direccion: Optional[str] = Field(None, max_length=300)
    telefono: Optional[str] = Field(None, max_length=50)
    correo: Optional[str] = Field(None, max_length=150)
    cif: Optional[str] = Field(None, max_length=50)


class PerfilEmpresaOut(BaseModel):
    id: int
    nombre_empresa: str
    logo_url: str | None
    color_principal: str
    direccion: str | None = None
    telefono: str | None = None
    correo: str | None = None
    cif: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
