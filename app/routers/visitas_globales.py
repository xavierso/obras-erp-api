"""
Vista global de visitas, a través de todas las obras de la empresa —
para la pestaña "Visitas" de la navegación inferior de la app, distinta
de la vista por obra (GET /obras/{id}/visitas). Disponible para admin e
inspector, igual que el resto de lo relacionado con visitas.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_empresa_id
from app.database import get_db
from app.models.obra import Obra
from app.models.visita import Visita
from app.schemas.visita import VisitaConObraOut
from app.services.storage_service import url_publica

router = APIRouter(prefix="/visitas", tags=["Visitas (vista global)"])


@router.get("", response_model=list[VisitaConObraOut])
async def listar_todas_las_visitas(
    limite: int = 50,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Visita)
        .join(Obra, Obra.id == Visita.obra_id)
        .where(Obra.usuario_id == empresa_id)
        .order_by(Visita.fecha.desc())
        .limit(limite)
    )
    visitas = result.scalars().all()

    salida = []
    for visita in visitas:
        await db.refresh(visita, attribute_names=["archivos", "obra"])
        salida.append(
            VisitaConObraOut(
                id=visita.id,
                obra_id=visita.obra_id,
                descripcion=visita.descripcion,
                fecha=visita.fecha,
                archivos=[
                    {
                        "id": a.id,
                        "tipo": a.tipo,
                        "nombre_original": a.nombre_original,
                        "url": url_publica(a.ruta_archivo),
                    }
                    for a in visita.archivos
                ],
                obra_nombre=visita.obra.nombre,
                obra_codigo=visita.obra.codigo,
            )
        )
    return salida
