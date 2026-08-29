"""
Modelo Incidencia e HistorialIncidencia.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoIncidencia(str, enum.Enum):
    NUEVA = "NUEVA"
    EN_PROCESO = "EN_PROCESO"
    RESUELTA = "RESUELTA"
    CERRADA = "CERRADA"


class TipoArchivoIncidencia(str, enum.Enum):
    FOTO = "foto"
    VIDEO = "video"
    DOCUMENTO = "documento"


class Incidencia(Base):
    __tablename__ = "incidencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=False, index=True)
    visita_id: Mapped[int | None] = mapped_column(ForeignKey("visitas.id", ondelete="SET NULL"), nullable=True, index=True)
    creador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    actividad_id: Mapped[int | None] = mapped_column(ForeignKey("actividades_cronograma.id", ondelete="SET NULL"), nullable=True, index=True)
    
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    fecha_deteccion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_resolucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    estado: Mapped[EstadoIncidencia] = mapped_column(
        SAEnum(EstadoIncidencia), default=EstadoIncidencia.NUEVA, nullable=False
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
    obra: Mapped["Obra"] = relationship(back_populates="incidencias")
    visita: Mapped["Visita | None"] = relationship(back_populates="incidencias")
    actividad: Mapped["ActividadCronograma | None"] = relationship()
    creador: Mapped["Usuario"] = relationship(foreign_keys=[creador_id], back_populates="incidencias_creadas")
    responsable: Mapped["Usuario | None"] = relationship(foreign_keys=[responsable_id], back_populates="incidencias_asignadas")
    
    historial: Mapped[list["HistorialIncidencia"]] = relationship(back_populates="incidencia", cascade="all, delete-orphan")
    archivos: Mapped[list["IncidenciaArchivo"]] = relationship(back_populates="incidencia", cascade="all, delete-orphan")
    tareas: Mapped[list["Tarea"]] = relationship(back_populates="incidencia")

    def __repr__(self) -> str:
        return f"<Incidencia id={self.id} codigo={self.codigo} estado={self.estado}>"


class HistorialIncidencia(Base):
    __tablename__ = "incidencias_historial"

    id: Mapped[int] = mapped_column(primary_key=True)
    incidencia_id: Mapped[int] = mapped_column(ForeignKey("incidencias.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    
    estado_anterior: Mapped[EstadoIncidencia | None] = mapped_column(SAEnum(EstadoIncidencia), nullable=True)
    estado_nuevo: Mapped[EstadoIncidencia] = mapped_column(SAEnum(EstadoIncidencia), nullable=False)
    
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    incidencia: Mapped["Incidencia"] = relationship(back_populates="historial")
    usuario: Mapped["Usuario"] = relationship(back_populates="historial_incidencias")

    def __repr__(self) -> str:
        return f"<HistorialIncidencia id={self.id} incidencia_id={self.incidencia_id} nuevo={self.estado_nuevo}>"


class IncidenciaArchivo(Base):
    __tablename__ = "incidencias_archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    incidencia_id: Mapped[int] = mapped_column(ForeignKey("incidencias.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tipo: Mapped[TipoArchivoIncidencia] = mapped_column(SAEnum(TipoArchivoIncidencia), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    incidencia: Mapped["Incidencia"] = relationship(back_populates="archivos")

    def __repr__(self) -> str:
        return f"<IncidenciaArchivo id={self.id} incidencia_id={self.incidencia_id} tipo={self.tipo}>"
