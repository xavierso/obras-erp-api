import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, Float, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Boolean, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoPresupuesto(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    PENDIENTE_APROBACION = "pendiente_aprobacion"
    APROBADO = "aprobado"
    EN_EJECUCION = "en_ejecucion"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    iva: Mapped[float] = mapped_column(Float, default=21.0, nullable=False)

    codigo: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    cliente_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(20), nullable=True)

    estado: Mapped[EstadoPresupuesto] = mapped_column(
        SAEnum(EstadoPresupuesto), default=EstadoPresupuesto.BORRADOR, nullable=False
    )
    es_version_activa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    coste_estimado_obra: Mapped[float | None] = mapped_column(Float, nullable=True)

    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"), nullable=True)
    obra: Mapped["Obra | None"] = relationship(back_populates="presupuestos")

    creador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    creador: Mapped["Usuario"] = relationship(foreign_keys=[creador_id])

    aprobador_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    aprobador: Mapped["Usuario | None"] = relationship(foreign_keys=[aprobador_id])
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    capitulos: Mapped[list["CapituloPresupuesto"]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan", order_by="CapituloPresupuesto.orden"
    )
    certificaciones: Mapped[list["Certificacion"]] = relationship(
        back_populates="presupuesto", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def coste_directo(self) -> float:
        return float(sum(capitulo.subtotal for capitulo in self.capitulos) or 0)

    @property
    def importe_iva(self) -> float:
        return float(self.coste_directo * (self.iva / 100))

    @property
    def total(self) -> float:
        return float(self.coste_directo + self.importe_iva)

    def __repr__(self) -> str:
        return f"<Presupuesto id={self.id} version={self.version} estado={self.estado}>"


class CapituloPresupuesto(Base):
    __tablename__ = "capitulos_presupuesto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id", ondelete="CASCADE"), nullable=False)
    presupuesto: Mapped["Presupuesto"] = relationship(back_populates="capitulos")

    padre_id: Mapped[int | None] = mapped_column(ForeignKey("capitulos_presupuesto.id", ondelete="CASCADE"), nullable=True)
    subcapitulos: Mapped[list["CapituloPresupuesto"]] = relationship(
        back_populates="padre", cascade="all, delete-orphan", order_by="CapituloPresupuesto.orden"
    )
    padre: Mapped["CapituloPresupuesto | None"] = relationship(back_populates="subcapitulos", remote_side=[id])

    partidas: Mapped[list["PartidaPresupuesto"]] = relationship(
        back_populates="capitulo", cascade="all, delete-orphan", order_by="PartidaPresupuesto.id"
    )

    @property
    def subtotal(self) -> float:
        return float(sum(partida.importe for partida in self.partidas) or 0)

    def __repr__(self) -> str:
        return f"<CapituloPresupuesto id={self.id} nombre={self.nombre}>"


class PartidaPresupuesto(Base):
    __tablename__ = "partidas_presupuesto"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    
    # Desglose de costes internos
    coste_base: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0) # Coste ejecución
    coste_material: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0)
    porcentaje_indirectos: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)
    porcentaje_comisiones: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)
    
    coste_unitario: Mapped[float | None] = mapped_column(Numeric(10, 2), default=0) # Coste total unitario calculado
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), default=0) # Venta final unitaria
    descuento_porcentaje: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)
    margen_porcentaje: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    capitulo_id: Mapped[int] = mapped_column(ForeignKey("capitulos_presupuesto.id", ondelete="CASCADE"), nullable=False)
    capitulo: Mapped["CapituloPresupuesto"] = relationship(back_populates="partidas")

    # Relación inversa (para navegar desde partida hacia el cronograma)
    actividades_cronograma: Mapped[list["ActividadCronograma"]] = relationship(
        back_populates="partida_presupuesto"
    )

    @property
    def precio_con_descuento(self) -> float:
        return float(self.precio_unitario) * (1 - float(self.descuento_porcentaje or 0) / 100)

    @property
    def importe(self) -> float:
        return float(self.cantidad) * self.precio_con_descuento

    @property
    def coste_total(self) -> float:
        return float(self.cantidad) * float(self.coste_unitario or 0)

    def __repr__(self) -> str:
        return f"<PartidaPresupuesto id={self.id} codigo={self.codigo}>"
