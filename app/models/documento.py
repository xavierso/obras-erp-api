"""
Modelo Documento, migrado desde bot_erp_obras/utils/categorias_documento.py
+ models/documento.py.

Se conservan las mismas categorías que ya usabas en el bot.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CategoriaDocumento(str, enum.Enum):
    PLANOS = "planos"
    PRESUPUESTOS = "presupuestos"
    CONTRATOS = "contratos"
    FACTURAS = "facturas"
    GARANTIAS = "garantias"
    TECNICA = "tecnica"


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    categoria: Mapped[CategoriaDocumento] = mapped_column(
        SAEnum(CategoriaDocumento), nullable=False
    )
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    obra: Mapped["Obra"] = relationship(back_populates="documentos")

    def __repr__(self) -> str:
        return f"<Documento id={self.id} categoria={self.categoria}>"
