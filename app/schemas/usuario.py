"""
Esquemas Pydantic: definen qué datos entran y salen de la API.
Nunca se expone hashed_password en ninguna respuesta.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.usuario import RolUsuario


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=100)


class UsuarioOut(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    is_active: bool
    rol: RolUsuario
    empresa_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
