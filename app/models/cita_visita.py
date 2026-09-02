"""
Modelo CitaVisita, migrado desde bot_erp_obras.

Representa una visita/cita PROGRAMADA a futuro (recordatorio), distinta de
Visita (que ya se realizó). Puede estar ligada a una obra formal (obra_id)
o a una referencia libre para obras potenciales/presupuestos todavía sin
formalizar (nombre_referencia) — al menos uno de los dos debe existir,
forzado con un CheckConstraint.

Cambio respecto al bot: chat_notificacion / chat_id (grupo de Telegram) no
tienen equivalente aquí — las notificaciones se envían por push (FCM) al
dispositivo del usuario, no a un chat. Esa pieza (registro de tokens de
dispositivo) se añadirá en la Fase B junto con la app móvil; por ahora el
scheduler deja preparado el punto de enganche (ver notificacion_service.py).
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoCita(str, enum.Enum):
    PENDIENTE = "pendiente"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class CitaVisita(Base):
    __tablename__ = "citas_visita"
    __table_args__ = (
        CheckConstraint(
            "obra_id IS NOT NULL OR nombre_referencia IS NOT NULL",
            name="ck_cita_obra_o_referencia",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    obra_id: Mapped[int | None] = mapped_column(
        ForeignKey("obras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nombre_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[EstadoCita] = mapped_column(
        SAEnum(EstadoCita), default=EstadoCita.PENDIENTE, nullable=False
    )

    # None = sin recordatorio. Si tiene valor, momento_recordatorio se
    # calcula al crear/reprogramar (ver services/cita_service.py) para que
    # el scheduler pueda consultarlo con un simple WHERE, sin recalcular.
    recordatorio_minutos_antes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    momento_recordatorio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    obra: Mapped["Obra | None"] = relationship(back_populates="citas", passive_deletes=True)
    visitas_potenciales: Mapped[list["VisitaPotencial"]] = relationship(
        back_populates="cita", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        ref = self.obra_id or self.nombre_referencia
        return f"<CitaVisita id={self.id} ref={ref} fecha_hora={self.fecha_hora}>"
