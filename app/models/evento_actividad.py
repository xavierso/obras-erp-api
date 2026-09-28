"""
Modelo EventoActividad para el registro de notificaciones y actividad reciente.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventoActividad(Base):
    __tablename__ = "eventos_actividad"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(500), nullable=False)
    
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    
    # Opcional, para enlazar a la obra, presupuesto, etc. de manera genérica
    entidad_relacionada_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entidad_relacionada_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    empresa: Mapped["Empresa"] = relationship()
    lecturas: Mapped[list["EventoActividadLectura"]] = relationship(back_populates="evento", cascade="all, delete-orphan")


class EventoActividadLectura(Base):
    __tablename__ = "eventos_actividad_lecturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    evento_id: Mapped[int] = mapped_column(ForeignKey("eventos_actividad.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    leido_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    evento: Mapped["EventoActividad"] = relationship(back_populates="lecturas")

