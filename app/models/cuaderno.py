import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoNotaCuaderno(str, enum.Enum):
    NOTA = "nota"
    CROQUIS = "croquis"
    VISITA = "visita"
    TAREA = "tarea"
    INCIDENCIA = "incidencia"
    PRESUPUESTO = "presupuesto"
    CERTIFICACION = "certificacion"
    PEDIDO = "pedido"
    OTRO = "otro"


class NotaCuaderno(Base):
    __tablename__ = "notas_cuaderno"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=False, index=True)
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo: Mapped[TipoNotaCuaderno] = mapped_column(SAEnum(TipoNotaCuaderno), default=TipoNotaCuaderno.NOTA, nullable=False)
    
    # JSON content storing canvas lines, text, embedded image metadata
    canvas_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Vinculación polimórfica simple (Fase 3/4)
    entidad_relacionada_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entidad_relacionada_id: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    obra: Mapped["Obra"] = relationship()
    autor: Mapped["Usuario"] = relationship()

    def __repr__(self) -> str:
        return f"<NotaCuaderno id={self.id} titulo={self.titulo} tipo={self.tipo}>"
