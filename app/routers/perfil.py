"""
Perfil de empresa editable, equivalente al módulo del bot original
(nombre + logo + color de marca, usado para personalizar los PDFs).
"""
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_db
from app.models.perfil_empresa import PerfilEmpresa
from app.models.usuario import Usuario
from app.schemas.perfil_empresa import PerfilEmpresaOut
from app.services.storage_service import ArchivoInvalido, guardar_archivo, url_publica

router = APIRouter(prefix="/perfil", tags=["Perfil de Empresa"])

PATRON_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _serializar(perfil: PerfilEmpresa) -> PerfilEmpresaOut:
    return PerfilEmpresaOut(
        id=perfil.id,
        nombre_empresa=perfil.nombre_empresa,
        logo_url=url_publica(perfil.logo_ruta) if perfil.logo_ruta else None,
        color_principal=perfil.color_principal,
        direccion=perfil.direccion,
        telefono=perfil.telefono,
        correo=perfil.correo,
        cif=perfil.cif,
        updated_at=perfil.updated_at,
    )


@router.get("", response_model=PerfilEmpresaOut)
async def obtener_perfil(
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PerfilEmpresa).where(PerfilEmpresa.usuario_id == admin.id)
    )
    perfil = result.scalar_one_or_none()
    if perfil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no has configurado el perfil de tu empresa",
        )
    return _serializar(perfil)


@router.put("", response_model=PerfilEmpresaOut)
async def actualizar_perfil(
    nombre_empresa: str = Form(...),
    color_principal: str = Form(default="#1E3A5F"),
    direccion: str | None = Form(default=None),
    telefono: str | None = Form(default=None),
    correo: str | None = Form(default=None),
    cif: str | None = Form(default=None),
    logo: UploadFile | None = File(default=None),
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not PATRON_COLOR_HEX.match(color_principal):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="color_principal debe ser un hex válido, ej. #1E3A5F",
        )

    result = await db.execute(
        select(PerfilEmpresa).where(PerfilEmpresa.usuario_id == admin.id)
    )
    perfil = result.scalar_one_or_none()

    if perfil is None:
        perfil = PerfilEmpresa(
            usuario_id=admin.id,
            nombre_empresa=nombre_empresa,
            color_principal=color_principal,
            direccion=direccion,
            telefono=telefono,
            correo=correo,
            cif=cif,
        )
        db.add(perfil)
    else:
        perfil.nombre_empresa = nombre_empresa
        perfil.color_principal = color_principal
        perfil.direccion = direccion
        perfil.telefono = telefono
        perfil.correo = correo
        perfil.cif = cif

    if logo is not None:
        try:
            subcarpeta = f"perfiles/{admin.id}"
            ruta_relativa, _ = await guardar_archivo(logo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        perfil.logo_ruta = ruta_relativa

    await db.commit()
    await db.refresh(perfil)
    return _serializar(perfil)
