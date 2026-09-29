from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
import enum
from sqlalchemy.orm import relationship
from app.database import Base

class ReminderChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    PUSH = "PUSH"

class ReminderStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    
    entidad_tipo = Column(String(50), nullable=False)
    entidad_id = Column(Integer, nullable=False)
    
    reminder_at = Column(DateTime(timezone=True), nullable=False, index=True)
    channel = Column(SQLEnum(ReminderChannel), default=ReminderChannel.IN_APP, nullable=False)
    status = Column(SQLEnum(ReminderStatus), default=ReminderStatus.PENDING, nullable=False)
    
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    empresa = relationship("Empresa")
    usuario = relationship("Usuario")
