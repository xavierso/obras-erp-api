"""
Modelo EventoCalendario.

Para almacenar eventos puros (Hitos, Reuniones, Entregas) que se crean directamente 
desde el calendario y no forman parte de otros modelos como Visitas, Tareas o Incidencias.
"""
import enum
from datetime import date, datetime, time, timezone

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoEventoCalendario(str, enum.Enum):
    HITO = "hito"
    REUNION = "reunion"
    ENTREGA = "entrega"
    OTRO = "otro"

class EstadoEventoCalendario(str, enum.Enum):
    PENDIENTE = "pendiente"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"

class EventoCalendario(Base):
    __tablename__ = "eventos_calendario"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    tipo: Mapped[TipoEventoCalendario] = mapped_column(SAEnum(TipoEventoCalendario), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=True, index=True)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    creador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True)
    
    estado: Mapped[EstadoEventoCalendario] = mapped_column(
        SAEnum(EstadoEventoCalendario), default=EstadoEventoCalendario.PENDIENTE, nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relaciones
    obra: Mapped["Obra | None"] = relationship(foreign_keys=[obra_id])
    responsable: Mapped["Usuario | None"] = relationship(foreign_keys=[responsable_id])
    creador: Mapped["Usuario"] = relationship(foreign_keys=[creador_id])

    def __repr__(self) -> str:
        return f"<EventoCalendario id={self.id} tipo={self.tipo} titulo={self.titulo} fecha={self.fecha}>"
