"""
Gestión documental por categorías. Restringido a admins — los inspectores
no gestionan documentación, solo registran visitas (ver deps.require_director, get_empresa_id).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_director, get_empresa_id, get_current_user
from app.database import get_db
from app.models.documento import CategoriaDocumento, Documento
from app.models.obra import Obra
from app.models.usuario import Usuario, RolUsuario
from app.schemas.documento import DocumentoOut
from app.services.storage_service import ArchivoInvalido, guardar_archivo, url_publica

router = APIRouter(prefix="/obras/{obra_id}/documentos", tags=["Documentos"])


async def _obtener_obra_de_la_empresa(obra_id: int, empresa_id: int, db: AsyncSession) -> Obra:
    result = await db.execute(
        select(Obra).where(Obra.id == obra_id, Obra.empresa_id == empresa_id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")
    return obra


def _serializar_documento(doc: Documento) -> DocumentoOut:
    return DocumentoOut(
        id=doc.id,
        obra_id=doc.obra_id,
        categoria=doc.categoria,
        nombre_original=doc.nombre_original,
        url=url_publica(doc.ruta_archivo),
        created_at=doc.created_at,
    )


@router.post("", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    obra_id: int,
    categoria: CategoriaDocumento = Form(...),
    archivo: UploadFile = File(...),
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)

    try:
        subcarpeta = f"obras/{obra.id}/documentos/{categoria.value}"
        ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
    except ArchivoInvalido as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    nuevo_documento = Documento(
        obra_id=obra.id,
        empresa_id=obra.empresa_id,
        usuario_id=admin.id,
        categoria=categoria,
        nombre_original=nombre_original,
        ruta_archivo=ruta_relativa,
    )
    db.add(nuevo_documento)
    await db.commit()
    await db.refresh(nuevo_documento)
    return _serializar_documento(nuevo_documento)


@router.get("", response_model=list[DocumentoOut])
async def listar_documentos(
    obra_id: int,
    categoria: CategoriaDocumento | None = None,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    query = select(Documento).where(Documento.obra_id == obra.id)
    if categoria is not None:
        query = query.where(Documento.categoria == categoria)
    result = await db.execute(query.order_by(Documento.created_at.desc()))
    return [_serializar_documento(d) for d in result.scalars().all()]


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_documento(
    obra_id: int,
    documento_id: int,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db)
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    result = await db.execute(
        select(Documento).where(Documento.id == documento_id, Documento.obra_id == obra.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
        
    await db.delete(doc)
    await db.commit()
    return None
