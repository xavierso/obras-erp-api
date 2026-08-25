"""
Generación de informes en PDF bajo demanda, equivalente al botón "Informes"
del bot original.
"""
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_director
from app.database import get_db
from app.models.obra import Obra
from app.models.perfil_empresa import PerfilEmpresa
from app.models.usuario import Usuario
from app.models.visita import Visita
from app.services.pdf_service import generar_informe_pdf

router = APIRouter(prefix="/obras/{obra_id}/informe", tags=["Informes"])


@router.get("")
async def generar_informe(
    obra_id: int,
    visita_id: int | None = None,
    admin: Usuario = Depends(require_director),
    db: AsyncSession = Depends(get_db),
):
    """
    Sin `visita_id`: informe completo con todas las visitas de la obra
    (comportamiento de siempre). Con `visita_id`: mismo formato de
    informe (portada + cronología), pero limitado a esa única visita —
    útil para compartir el reporte de una visita puntual sin mandar todo
    el historial.
    """
    result = await db.execute(
        select(Obra).where(Obra.id == obra_id, Obra.usuario_id == admin.id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")

    query = select(Visita).where(Visita.obra_id == obra.id)
    if visita_id is not None:
        query = query.where(Visita.id == visita_id)
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
        select(PerfilEmpresa).where(PerfilEmpresa.usuario_id == admin.id)
    )
    perfil = result.scalar_one_or_none()

    pdf_bytes = generar_informe_pdf(
        obra=obra,
        visitas=visitas,
        nombre_empresa=perfil.nombre_empresa if perfil else None,
        color_principal=perfil.color_principal if perfil else None,
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
