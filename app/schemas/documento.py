from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.documento import CategoriaDocumento


class DocumentoOut(BaseModel):
    id: int
    obra_id: int
    categoria: CategoriaDocumento
    nombre_original: str
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentoConObraOut(DocumentoOut):
    """Para la vista global de documentos (todas las obras)."""
    obra_nombre: str
    obra_codigo: str
