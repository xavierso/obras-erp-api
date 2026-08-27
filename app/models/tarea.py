"""
Modelo Tarea e HistorialTarea.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoTarea(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADA = "COMPLETADA"
    VENCIDA = "VENCIDA"

class TipoArchivoTarea(str, enum.Enum):
    FOTO = "foto"
    VIDEO = "video"
    DOCUMENTO = "documento"


class Tarea(Base):
    __tablename__ = "tareas"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=False, index=True)
    visita_id: Mapped[int | None] = mapped_column(ForeignKey("visitas.id", ondelete="CASCADE"), nullable=True, index=True)
    creador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    incidencia_id: Mapped[int | None] = mapped_column(ForeignKey("incidencias.id", ondelete="CASCADE"), nullable=True, index=True)
    
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[EstadoTarea] = mapped_column(
        SAEnum(EstadoTarea), default=EstadoTarea.PENDIENTE, nullable=False
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
    obra: Mapped["Obra"] = relationship(back_populates="tareas")
    visita: Mapped["Visita | None"] = relationship(back_populates="tareas")
    incidencia: Mapped["Incidencia | None"] = relationship(back_populates="tareas")
    creador: Mapped["Usuario"] = relationship(foreign_keys=[creador_id], back_populates="tareas_creadas")
    responsable: Mapped["Usuario | None"] = relationship(foreign_keys=[responsable_id], back_populates="tareas_asignadas")
    historial: Mapped[list["HistorialTarea"]] = relationship(back_populates="tarea", cascade="all, delete-orphan")
    archivos: Mapped[list["TareaArchivo"]] = relationship(back_populates="tarea", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tarea id={self.id} titulo={self.titulo} estado={self.estado}>"


class HistorialTarea(Base):
    __tablename__ = "tareas_historial"

    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    
    estado_anterior: Mapped[EstadoTarea | None] = mapped_column(SAEnum(EstadoTarea), nullable=True)
    estado_nuevo: Mapped[EstadoTarea] = mapped_column(SAEnum(EstadoTarea), nullable=False)
    
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tarea: Mapped["Tarea"] = relationship(back_populates="historial")
    usuario: Mapped["Usuario"] = relationship(back_populates="historial_tareas")

    def __repr__(self) -> str:
        return f"<HistorialTarea id={self.id} tarea_id={self.tarea_id} nuevo={self.estado_nuevo}>"


class TareaArchivo(Base):
    __tablename__ = "tareas_archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    tarea_id: Mapped[int] = mapped_column(ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tipo: Mapped[TipoArchivoTarea] = mapped_column(SAEnum(TipoArchivoTarea), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tarea: Mapped["Tarea"] = relationship(back_populates="archivos")

    def __repr__(self) -> str:
        return f"<TareaArchivo id={self.id} tarea_id={self.tarea_id} tipo={self.tipo}>"
