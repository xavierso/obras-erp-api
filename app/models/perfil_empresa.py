"""
Modelo PerfilEmpresa, migrado desde bot_erp_obras/models/perfil_empresa.py.

Cambio respecto al original: en el bot el perfil era único y global (una
sola empresa usando el bot). Aquí la API es multi-usuario, así que cada
Usuario tiene su propio PerfilEmpresa (relación 1 a 1) — útil si en el
futuro varias empresas usan la misma API.
"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PerfilEmpresa(Base):
    __tablename__ = "perfiles_empresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    nombre_empresa: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_ruta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color_principal: Mapped[str] = mapped_column(String(7), nullable=False, default="#1E3A5F")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="perfil_empresa")

    def __repr__(self) -> str:
        return f"<PerfilEmpresa id={self.id} nombre_empresa={self.nombre_empresa}>"
