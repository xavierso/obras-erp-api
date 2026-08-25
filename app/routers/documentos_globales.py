"""
Vista global de documentos de todas las obras de la empresa — para la
pestaña "Documentos" de la navegación inferior. Restringido a admin,
igual que el resto de la gestión documental.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_director
from app.database import get_db
from app.models.documento import CategoriaDocumento, Documento
from app.models.obra import Obra
from app.models.usuario import Usuario
from app.schemas.documento import DocumentoConObraOut
from app.services.storage_service import url_publica

router = APIRouter(prefix="/documentos", tags=["Documentos (vista global)"])


@router.get("", response_model=list[DocumentoConObraOut])
async def listar_todos_los_documentos(
    categoria: CategoriaDocumento | None = None,
    admin: Usuario = Depends(require_director),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Documento)
        .join(Obra, Obra.id == Documento.obra_id)
        .where(Obra.usuario_id == admin.id)
    )
    if categoria is not None:
        query = query.where(Documento.categoria == categoria)

    result = await db.execute(query.order_by(Documento.created_at.desc()))
    documentos = result.scalars().all()

    salida = []
    for documento in documentos:
        await db.refresh(documento, attribute_names=["obra"])
        salida.append(
            DocumentoConObraOut(
                id=documento.id,
                obra_id=documento.obra_id,
                categoria=documento.categoria,
                nombre_original=documento.nombre_original,
                url=url_publica(documento.ruta_archivo),
                created_at=documento.created_at,
                obra_nombre=documento.obra.nombre,
                obra_codigo=documento.obra.codigo,
            )
        )
    return salida
