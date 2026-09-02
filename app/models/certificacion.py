import enum
from datetime import date, datetime, timezone
from sqlalchemy import Integer, String, Float, Date, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class EstadoCertificacion(str, enum.Enum):
    BORRADOR = "borrador"
    EMITIDA = "emitida"
    FACTURADA = "facturada"
    COBRADA = "cobrada"
    ANULADA = "anulada"

class Certificacion(Base):
    __tablename__ = "certificaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id"), nullable=False)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    estado: Mapped[EstadoCertificacion] = mapped_column(
        SAEnum(EstadoCertificacion, name="estadocertificacion"), default=EstadoCertificacion.BORRADOR, nullable=False
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    presupuesto = relationship("Presupuesto", back_populates="certificaciones")
    lineas = relationship(
        "LineaCertificacion", back_populates="certificacion", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LineaCertificacion(Base):
    __tablename__ = "lineas_certificacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    certificacion_id: Mapped[int] = mapped_column(ForeignKey("certificaciones.id"), nullable=False)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas_presupuesto.id"), nullable=False)
    
    # La cantidad ejecutada en el periodo que cubre esta certificación
    cantidad_actual: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relaciones
    certificacion = relationship("Certificacion", back_populates="lineas")
    partida = relationship("PartidaPresupuesto")
