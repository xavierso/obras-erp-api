"""
Modelo Obra, migrado desde bot_erp_obras/models/.

Cambios respecto al original:
- chat_id (Telegram) -> usuario_id (FK a Usuario), como dueño/creador de la obra.
  Se mantiene chat_id_telegram como campo OPCIONAL por si en el futuro se
  quiere seguir usando el bot de Telegram en paralelo a la app (notificaciones
  al grupo de obra, por ejemplo), tal y como comentabas que querías valorar.
- El resto de campos y el enum de estados se conservan igual.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, Float, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoObra(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_EJECUCION = "en_ejecucion"
    EN_PAUSA = "en_pausa"
    FINALIZADA = "finalizada"
    ENTREGADA = "entregada"
    ARCHIVADA = "archivada"


class Obra(Base):
    __tablename__ = "obras"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cliente: Mapped[str | None] = mapped_column(String(200), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    estado: Mapped[EstadoObra] = mapped_column(
        SAEnum(EstadoObra), default=EstadoObra.PENDIENTE, nullable=False
    )

    # Añadidos para la ficha de obra de la app (progreso visual, no formal).
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    superficie_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    progreso_porcentaje: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Texto libre tipo "Preparación de sellado" — descriptivo, NO sustituye
    # al enum `estado` (que sigue gobernando el banner/flujo formal).
    estado_actual_texto: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Compatibilidad opcional con el bot de Telegram existente.
    chat_id_telegram: Mapped[str | None] = mapped_column(String(50), nullable=True)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    propietario: Mapped["Usuario"] = relationship(back_populates="obras")
    visitas: Mapped[list["Visita"]] = relationship(
        back_populates="obra", cascade="all, delete-orphan"
    )
    documentos: Mapped[list["Documento"]] = relationship(
        back_populates="obra", cascade="all, delete-orphan"
    )
    citas: Mapped[list["CitaVisita"]] = relationship(back_populates="obra")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Obra id={self.id} codigo={self.codigo} estado={self.estado}>"
