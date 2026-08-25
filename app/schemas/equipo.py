from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.invitacion import EstadoInvitacion
from app.models.usuario import RolUsuario


class InvitacionCreate(BaseModel):
    email: EmailStr
    rol: RolUsuario = Field(default=RolUsuario.INSPECTOR)


class InvitacionOut(BaseModel):
    id: int
    email: str
    rol: RolUsuario
    estado: EstadoInvitacion
    created_at: datetime
    expira_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AceptarInvitacionRequest(BaseModel):
    token: str
    nombre: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=100)


class MiembroEquipoOut(BaseModel):
    id: int
    nombre: str
    email: str
    rol: RolUsuario
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
