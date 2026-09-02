"""
Modelo Visita, migrado desde bot_erp_obras.

Cambio respecto al original: en el bot las fotos/vídeos se guardaban como
file_id de Telegram (no se descargaban). Aquí no hay servidores de Telegram
detrás, así que los archivos se suben y almacenan de verdad -> tabla
VisitaArchivo, una fila por cada foto/vídeo adjunto a la visita.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoArchivoVisita(str, enum.Enum):
    FOTO = "foto"
    VIDEO = "video"


class Visita(Base):
    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id"), nullable=False, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    obra: Mapped["Obra"] = relationship(back_populates="visitas")
    archivos: Mapped[list["VisitaArchivo"]] = relationship(
        back_populates="visita", cascade="all, delete-orphan"
    )
    tareas: Mapped[list["Tarea"]] = relationship(
        back_populates="visita"
    )
    incidencias: Mapped[list["Incidencia"]] = relationship(
        back_populates="visita"
    )

    def __repr__(self) -> str:
        return f"<Visita id={self.id} obra_id={self.obra_id} fecha={self.fecha}>"


class VisitaArchivo(Base):
    """Cada foto o vídeo adjunto a una visita, guardado ya como archivo real."""
    __tablename__ = "visita_archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    visita_id: Mapped[int] = mapped_column(ForeignKey("visitas.id"), nullable=False, index=True)
    tipo: Mapped[TipoArchivoVisita] = mapped_column(SAEnum(TipoArchivoVisita), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    visita: Mapped["Visita"] = relationship(back_populates="archivos")
