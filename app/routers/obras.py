"""
CRUD de Obra.

Con el módulo de Equipo: las obras pertenecen a una "empresa" (el admin
dueño de la cuenta). Los inspectores de esa empresa VEN las mismas obras
(filtrado por empresa_id, no por su propio usuario_id), pero solo un
admin puede crear obras o editarlas (require_admin).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_empresa_id, require_admin
from app.database import get_db
from app.models.obra import Obra
from app.models.usuario import Usuario
from app.models.visita import Visita
from app.schemas.obra import ObraCreate, ObraDetalleUpdate, ObraEstadoUpdate, ObraOut
from app.services.obra_service import generar_codigo_obra

router = APIRouter(prefix="/obras", tags=["Obras"])


async def _obtener_obra_de_la_empresa(obra_id: int, empresa_id: int, db: AsyncSession) -> Obra:
    result = await db.execute(
        select(Obra).where(Obra.id == obra_id, Obra.usuario_id == empresa_id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")
    return obra


async def _construir_obra_out(obra: Obra, db: AsyncSession) -> ObraOut:
    """Añade total_visitas y ultima_visita_fecha, calculados aparte."""
    result = await db.execute(
        select(func.count(Visita.id), func.max(Visita.fecha)).where(Visita.obra_id == obra.id)
    )
    total, ultima = result.one()
    item = ObraOut.model_validate(obra)
    item.total_visitas = total or 0
    item.ultima_visita_fecha = ultima
    return item


@router.post("", response_model=ObraOut, status_code=status.HTTP_201_CREATED)
async def crear_obra(
    datos: ObraCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    codigo = await generar_codigo_obra(db)
    nueva_obra = Obra(
        codigo=codigo,
        nombre=datos.nombre,
        cliente=datos.cliente,
        direccion=datos.direccion,
        usuario_id=admin.id,
    )
    db.add(nueva_obra)
    await db.commit()
    await db.refresh(nueva_obra)
    return await _construir_obra_out(nueva_obra, db)


@router.get("", response_model=list[ObraOut])
async def listar_obras(
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Obra).where(Obra.usuario_id == empresa_id).order_by(Obra.created_at.desc())
    )
    obras = result.scalars().all()
    if not obras:
        return []

    obra_ids = [o.id for o in obras]
    result = await db.execute(
        select(Visita.obra_id, func.count(Visita.id), func.max(Visita.fecha))
        .where(Visita.obra_id.in_(obra_ids))
        .group_by(Visita.obra_id)
    )
    stats_por_obra = {fila[0]: (fila[1], fila[2]) for fila in result.all()}

    salida = []
    for obra in obras:
        total, ultima = stats_por_obra.get(obra.id, (0, None))
        item = ObraOut.model_validate(obra)
        item.total_visitas = total
        item.ultima_visita_fecha = ultima
        salida.append(item)
    return salida


@router.get("/{obra_id}", response_model=ObraOut)
async def consultar_obra(
    obra_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    return await _construir_obra_out(obra, db)


@router.patch("/{obra_id}/estado", response_model=ObraOut)
async def cambiar_estado_obra(
    obra_id: int,
    datos: ObraEstadoUpdate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, admin.id, db)
    obra.estado = datos.estado
    await db.commit()
    await db.refresh(obra)
    return await _construir_obra_out(obra, db)


@router.patch("/{obra_id}", response_model=ObraOut)
async def actualizar_detalle_obra(
    obra_id: int,
    datos: ObraDetalleUpdate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza los campos de la ficha de obra (nombre, cliente, dirección,
    fecha de inicio, superficie, progreso visual, texto de estado actual).
    No toca el enum `estado` formal — para eso está /estado.
    """
    obra = await _obtener_obra_de_la_empresa(obra_id, admin.id, db)
    datos_dict = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_dict.items():
        setattr(obra, campo, valor)
    await db.commit()
    await db.refresh(obra)
    return await _construir_obra_out(obra, db)
