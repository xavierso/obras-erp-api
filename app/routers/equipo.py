"""
Gestión de equipo: el admin invita inspectores, ve quién forma parte de
su equipo, y puede darlos de baja. Todo este router es solo para admins
(ver require_admin) — un inspector ni siquiera puede consultar su propio
equipo, porque no gestiona nada, solo registra visitas.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_db
from app.models.invitacion import EstadoInvitacion, Invitacion
from app.models.usuario import RolUsuario, Usuario
from app.schemas.equipo import InvitacionCreate, InvitacionOut, MiembroEquipoOut
from app.services.invitacion_service import (
    calcular_expiracion,
    enviar_email_invitacion,
    generar_token,
)

router = APIRouter(prefix="/equipo", tags=["Equipo"])


class InvitacionCreadaOut(InvitacionOut):
    # Se incluye el token en la respuesta SOLO porque todavía no hay envío
    # real de email configurado (ver invitacion_service.py) — así puedes
    # probar el flujo de aceptación a mano. Cuando haya email real, este
    # campo debería quitarse de la respuesta.
    token: str


class ResumenEquipo(BaseModel):
    miembros: list[MiembroEquipoOut]
    invitaciones_pendientes: list[InvitacionOut]


@router.post("/invitar", response_model=InvitacionCreadaOut, status_code=status.HTTP_201_CREATED)
async def invitar_inspector(
    datos: InvitacionCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Usuario).where(Usuario.email == datos.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese email",
        )

    result = await db.execute(
        select(Invitacion).where(
            Invitacion.email == datos.email,
            Invitacion.admin_id == admin.id,
            Invitacion.estado == EstadoInvitacion.PENDIENTE,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya hay una invitación pendiente para ese email",
        )

    nueva_invitacion = Invitacion(
        email=datos.email,
        admin_id=admin.id,
        token=generar_token(),
        expira_at=calcular_expiracion(),
    )
    db.add(nueva_invitacion)
    await db.commit()
    await db.refresh(nueva_invitacion)

    await enviar_email_invitacion(datos.email, nueva_invitacion.token, admin.nombre)

    return InvitacionCreadaOut(
        id=nueva_invitacion.id,
        email=nueva_invitacion.email,
        estado=nueva_invitacion.estado,
        created_at=nueva_invitacion.created_at,
        expira_at=nueva_invitacion.expira_at,
        token=nueva_invitacion.token,
    )


@router.get("", response_model=ResumenEquipo)
async def ver_equipo(
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario).where(Usuario.admin_id == admin.id).order_by(Usuario.created_at.desc())
    )
    miembros = result.scalars().all()

    result = await db.execute(
        select(Invitacion)
        .where(
            Invitacion.admin_id == admin.id,
            Invitacion.estado == EstadoInvitacion.PENDIENTE,
            Invitacion.expira_at > datetime.now(timezone.utc),
        )
        .order_by(Invitacion.created_at.desc())
    )
    invitaciones = result.scalars().all()

    return ResumenEquipo(
        miembros=[MiembroEquipoOut.model_validate(m) for m in miembros],
        invitaciones_pendientes=[InvitacionOut.model_validate(i) for i in invitaciones],
    )


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_de_baja_inspector(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.admin_id == admin.id,
            Usuario.rol == RolUsuario.INSPECTOR,
        )
    )
    inspector = result.scalar_one_or_none()
    if inspector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspector no encontrado")

    # Baja lógica, no se borra: conserva el historial de visitas que
    # haya registrado (Visita.usuario_id sigue apuntando a él).
    inspector.is_active = False
    await db.commit()


@router.delete("/invitaciones/{invitacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_invitacion(
    invitacion_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invitacion).where(Invitacion.id == invitacion_id, Invitacion.admin_id == admin.id)
    )
    invitacion = result.scalar_one_or_none()
    if invitacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitación no encontrada")

    await db.delete(invitacion)
    await db.commit()
