"""
Modelo VisitaPotencial, migrado desde bot_erp_obras.

Versión ligera de Visita, asociada a una CitaVisita (no a una Obra formal).
Mismos campos que Visita (fecha, observaciones, fotos, vídeos, usuario),
pero pensada para un único "parte de trabajo" puntual en vez de acumularse
en un historial largo.
"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.visita import TipoArchivoVisita


class VisitaPotencial(Base):
    __tablename__ = "visitas_potenciales"

    id: Mapped[int] = mapped_column(primary_key=True)
    cita_id: Mapped[int] = mapped_column(
        ForeignKey("citas_visita.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    cita: Mapped["CitaVisita"] = relationship(back_populates="visitas_potenciales")
    archivos: Mapped[list["VisitaPotencialArchivo"]] = relationship(
        back_populates="visita_potencial", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VisitaPotencial id={self.id} cita_id={self.cita_id}>"


class VisitaPotencialArchivo(Base):
    __tablename__ = "visita_potencial_archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    visita_potencial_id: Mapped[int] = mapped_column(
        ForeignKey("visitas_potenciales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[TipoArchivoVisita] = mapped_column(SAEnum(TipoArchivoVisita), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    visita_potencial: Mapped["VisitaPotencial"] = relationship(back_populates="archivos")
