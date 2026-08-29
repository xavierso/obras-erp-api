from datetime import date, datetime, timezone
import enum

from sqlalchemy import Date, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoActividad(str, enum.Enum):
    NO_INICIADA = "no_iniciada"
    EN_EJECUCION = "en_ejecucion"
    COMPLETADA = "completada"
    RETRASADA = "retrasada"
    CANCELADA = "cancelada"


class ActividadCronograma(Base):
    __tablename__ = "actividades_cronograma"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=False)
    
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    porcentaje_avance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # El estado real se calculará dinámicamente, pero guardamos un estado base por si hay cancelaciones
    estado_base: Mapped[EstadoActividad] = mapped_column(
        SAEnum(EstadoActividad), default=EstadoActividad.NO_INICIADA, nullable=False
    )
    
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    prioridad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Hito support (Phase 8)
    es_hito: Mapped[bool] = mapped_column(default=False, nullable=False)

    partida_presupuesto_id: Mapped[int | None] = mapped_column(
        ForeignKey("partidas_presupuesto.id", ondelete="SET NULL"), nullable=True
    )

    obra: Mapped["Obra"] = relationship()
    responsable: Mapped["Usuario"] = relationship()
    partida_presupuesto: Mapped["PartidaPresupuesto"] = relationship(back_populates="actividades_cronograma")
    
    # Relaciones futuras con Tareas e Incidencias se añadirán en sus respectivos modelos

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def estado(self) -> EstadoActividad:
        """Cálculo dinámico del estado basado en porcentaje y fechas."""
        if self.estado_base == EstadoActividad.CANCELADA:
            return EstadoActividad.CANCELADA
            
        if self.porcentaje_avance >= 100:
            return EstadoActividad.COMPLETADA
            
        hoy = date.today()
        
        # Si no está completada y hoy es mayor que la fecha fin prevista, está retrasada
        if hoy > self.fecha_fin_prevista and self.porcentaje_avance < 100:
            return EstadoActividad.RETRASADA
            
        if self.porcentaje_avance > 0:
            return EstadoActividad.EN_EJECUCION
            
        return EstadoActividad.NO_INICIADA

    def __repr__(self) -> str:
        return f"<ActividadCronograma id={self.id} nombre={self.nombre} avance={self.porcentaje_avance}%>"
