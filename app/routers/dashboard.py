from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_db
from app.models.usuario import Usuario
from app.services.dashboard_service import obtener_resumen_dashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ResumenDashboard(BaseModel):
    obras_activas: int
    visitas_hoy: int
    visitas_semana: int
    documentos_nuevos_semana: int


@router.get("/resumen", response_model=ResumenDashboard)
async def resumen(
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await obtener_resumen_dashboard(admin.id, db)
