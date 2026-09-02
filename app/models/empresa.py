"""
Modelo Empresa, que actúa como el Tenant principal del sistema.
"""
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cif: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(150), nullable=True)
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

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="empresa")
    obras: Mapped[list["Obra"]] = relationship(back_populates="empresa")

    def __repr__(self) -> str:
        return f"<Empresa id={self.id} nombre={self.nombre}>"
