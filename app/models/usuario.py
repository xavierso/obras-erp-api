"""
Modelo Usuario.

NUEVO respecto al proyecto original: en el bot de Telegram la identidad
del usuario era el chat_id. Aquí la identidad real es email + contraseña,
y cada Obra pasa a pertenecer a una "empresa" (representada por un
Usuario admin) en vez de estar vinculada a un chat_id de Telegram.

NUEVO en este bloque (Equipo): un Usuario tiene un rol.
- ADMIN: dueño de la cuenta/empresa. admin_id queda en None.
- INSPECTOR: pertenece a la cuenta de un admin (admin_id apunta a él).
  Solo puede ver obras y registrar/ver visitas — nada más.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RolUsuario(str, enum.Enum):
    ADMIN = "admin"
    INSPECTOR = "inspector"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    rol: Mapped[RolUsuario] = mapped_column(
        SAEnum(RolUsuario), default=RolUsuario.ADMIN, nullable=False
    )
    # Solo tiene valor si rol == INSPECTOR: apunta al Usuario (admin) al
    # que pertenece. Los admins tienen admin_id = None.
    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    obras: Mapped[list["Obra"]] = relationship(back_populates="propietario")
    perfil_empresa: Mapped["PerfilEmpresa | None"] = relationship(
        back_populates="usuario", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id} email={self.email} rol={self.rol}>"
