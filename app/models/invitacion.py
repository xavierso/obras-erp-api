"""
Modelo Invitacion: un admin invita a un inspector por email. El inspector
recibe (fuera del alcance de este bloque, sin envío de email real todavía
— ver services/invitacion_service.py) un enlace con un token único, con el
que se registra y queda vinculado a la cuenta del admin que lo invitó.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoInvitacion(str, enum.Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    EXPIRADA = "expirada"


class Invitacion(Base):
    __tablename__ = "invitaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    estado: Mapped[EstadoInvitacion] = mapped_column(
        SAEnum(EstadoInvitacion), default=EstadoInvitacion.PENDIENTE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expira_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<Invitacion id={self.id} email={self.email} estado={self.estado}>"
