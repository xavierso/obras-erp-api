from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_empresa_id, require_inspector_or_higher, require_director
from app.database import get_db
from app.models.obra import Obra
from app.models.usuario import Usuario
from app.models.cuaderno import NotaCuaderno
from app.schemas.cuaderno import NotaCuadernoCreate, NotaCuadernoUpdate, NotaCuadernoList, NotaCuadernoDetail


router = APIRouter(prefix="/obras/{obra_id}/cuaderno", tags=["Cuaderno"])


async def _obtener_obra_de_la_empresa(obra_id: int, empresa_id: int, db: AsyncSession) -> Obra:
    result = await db.execute(
        select(Obra).where(Obra.id == obra_id, Obra.empresa_id == empresa_id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")
    return obra


@router.post("", response_model=NotaCuadernoDetail, status_code=status.HTTP_201_CREATED)
async def crear_nota(
    obra_id: int,
    nota_in: NotaCuadernoCreate,
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)

    nueva_nota = NotaCuaderno(
        obra_id=obra.id,
        autor_id=usuario.id,
        titulo=nota_in.titulo,
        tipo=nota_in.tipo,
        canvas_data=nota_in.canvas_data,
        entidad_relacionada_tipo=nota_in.entidad_relacionada_tipo,
        entidad_relacionada_id=nota_in.entidad_relacionada_id,
    )
    
    db.add(nueva_nota)
    await db.commit()
    await db.refresh(nueva_nota)
    
    return nueva_nota


@router.get("", response_model=list[NotaCuadernoList])
async def listar_notas(
    obra_id: int,
    tipo: str = None,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    
    query = select(NotaCuaderno).where(NotaCuaderno.obra_id == obra.id)
    if tipo:
        from sqlalchemy import or_
        query = query.where(
            or_(
                NotaCuaderno.tipo == tipo,
                NotaCuaderno.entidad_relacionada_tipo == tipo
            )
        )
        
    query = query.order_by(NotaCuaderno.created_at.desc())
    
    result = await db.execute(query)
    notas = result.scalars().all()
    
    return notas


@router.get("/{nota_id}", response_model=NotaCuadernoDetail)
async def obtener_nota(
    obra_id: int,
    nota_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    
    result = await db.execute(
        select(NotaCuaderno).where(NotaCuaderno.id == nota_id, NotaCuaderno.obra_id == obra.id)
    )
    nota = result.scalar_one_or_none()
    
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota no encontrada")
        
    return nota


@router.put("/{nota_id}", response_model=NotaCuadernoDetail)
async def actualizar_nota(
    obra_id: int,
    nota_id: int,
    nota_in: NotaCuadernoUpdate,
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    
    result = await db.execute(
        select(NotaCuaderno).where(NotaCuaderno.id == nota_id, NotaCuaderno.obra_id == obra.id)
    )
    nota = result.scalar_one_or_none()
    
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota no encontrada")
        
    # Validar permisos: solo el creador o un admin puede editar
    if nota.autor_id != usuario.id and not usuario.es_director:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para editar esta nota")

    if nota_in.titulo is not None:
        nota.titulo = nota_in.titulo
    if nota_in.tipo is not None:
        nota.tipo = nota_in.tipo
    if nota_in.canvas_data is not None:
        nota.canvas_data = nota_in.canvas_data
    if nota_in.preview_url is not None:
        nota.preview_url = nota_in.preview_url
    if nota_in.entidad_relacionada_tipo is not None:
        nota.entidad_relacionada_tipo = nota_in.entidad_relacionada_tipo
    if nota_in.entidad_relacionada_id is not None:
        nota.entidad_relacionada_id = nota_in.entidad_relacionada_id
        
    await db.commit()
    await db.refresh(nota)
    
    return nota


@router.delete("/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_nota(
    obra_id: int,
    nota_id: int,
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    
    result = await db.execute(
        select(NotaCuaderno).where(NotaCuaderno.id == nota_id, NotaCuaderno.obra_id == obra.id)
    )
    nota = result.scalar_one_or_none()
    
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota no encontrada")
        
    # Validar permisos
    if nota.autor_id != usuario.id and not usuario.es_director:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para eliminar esta nota")
        
    await db.delete(nota)
    await db.commit()
    return None
