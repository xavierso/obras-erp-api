"""
Generación de informes en PDF bajo demanda, equivalente al botón "Informes"
del bot original.
"""
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_director, get_empresa_id
from app.database import get_db
from app.models.obra import Obra
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.visita import Visita
from app.services.pdf_service import generar_informe_pdf

router = APIRouter(prefix="/obras/{obra_id}/informe", tags=["Informes"])


@router.get("")
async def generar_informe(
    obra_id: int,
    visita_id: int | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    admin: Usuario = Depends(require_director),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Sin `visita_id`: informe completo con todas las visitas de la obra
    (comportamiento de siempre). Con `visita_id`: mismo formato de
    informe (portada + cronología), pero limitado a esa única visita.
    Además, permite filtrar por un rango de fechas con `fecha_inicio` y `fecha_fin`.
    """
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Obra)
        .where(Obra.id == obra_id, Obra.empresa_id == empresa_id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")

    query = select(Visita).options(
        selectinload(Visita.archivos)
    ).where(Visita.obra_id == obra.id)
    if visita_id is not None:
        query = query.where(Visita.id == visita_id)
    
    if fecha_inicio:
        query = query.where(Visita.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.where(Visita.fecha <= fecha_fin)
        
    query = query.order_by(Visita.fecha.asc())

    result = await db.execute(query)
    visitas = result.scalars().all()

    if visita_id is not None and not visitas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visita no encontrada en esta obra"
        )

    for v in visitas:
        await db.refresh(v, attribute_names=["archivos"])

    result = await db.execute(
        select(Empresa).where(Empresa.id == empresa_id)
    )
    perfil = result.scalar_one_or_none()

    pdf_bytes = generar_informe_pdf(
        obra=obra,
        visitas=visitas,
        nombre_empresa=perfil.nombre if perfil else None,
        color_principal=perfil.color_principal if perfil else None,
        logo_ruta=perfil.logo_ruta if perfil else None
    )

    if visita_id is not None:
        nombre_archivo = f"informe_{obra.codigo}_visita_{visita_id}.pdf"
    else:
        nombre_archivo = f"informe_{obra.codigo}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
