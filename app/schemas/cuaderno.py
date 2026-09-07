from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.cuaderno import TipoNotaCuaderno


class NotaCuadernoBase(BaseModel):
    titulo: Optional[str] = None
    tipo: TipoNotaCuaderno = TipoNotaCuaderno.NOTA
    entidad_relacionada_tipo: Optional[str] = None
    entidad_relacionada_id: Optional[int] = None
    # No exponemos obra_id ni autor_id en la base, 
    # obra_id viene de la URL y autor_id del token


class NotaCuadernoCreate(NotaCuadernoBase):
    canvas_data: Optional[dict[str, Any]] = None


class NotaCuadernoUpdate(NotaCuadernoBase):
    canvas_data: Optional[dict[str, Any]] = None
    preview_url: Optional[str] = None


class NotaCuadernoList(NotaCuadernoBase):
    id: int
    obra_id: int
    autor_id: int
    preview_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Excluimos canvas_data para no saturar los listados
    
    model_config = ConfigDict(from_attributes=True)


class NotaCuadernoDetail(NotaCuadernoList):
    # En el detalle sí devolvemos el canvas_data
    canvas_data: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
