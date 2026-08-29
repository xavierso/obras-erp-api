from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_empresa_id
from app.database import get_db
from app.services.dashboard_service import obtener_resumen_dashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ResumenDashboard(BaseModel):
    obras_activas: int
    visitas_hoy: int
    visitas_semana: int
    documentos_nuevos_semana: int
    actividades_retrasadas_total: int
    obras_avance: list[dict]


@router.get("/resumen", response_model=ResumenDashboard)
async def resumen(
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    return await obtener_resumen_dashboard(empresa_id, db)
