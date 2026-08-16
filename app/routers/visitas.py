"""
Registro de visitas con fotos/vídeos — el corazón del trabajo del rol
Inspector. Tanto admin como inspectores de la misma empresa pueden
registrar y ver visitas de cualquier obra de esa empresa.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_empresa_id
from app.database import get_db
from app.models.obra import Obra
from app.models.usuario import Usuario
from app.models.visita import TipoArchivoVisita, Visita, VisitaArchivo
from app.schemas.visita import VisitaOut
from app.services.storage_service import ArchivoInvalido, guardar_archivo, url_publica

router = APIRouter(prefix="/obras/{obra_id}/visitas", tags=["Visitas"])

EXTENSIONES_VIDEO = {".mp4", ".mov"}


async def _obtener_obra_de_la_empresa(obra_id: int, empresa_id: int, db: AsyncSession) -> Obra:
    result = await db.execute(
        select(Obra).where(Obra.id == obra_id, Obra.usuario_id == empresa_id)
    )
    obra = result.scalar_one_or_none()
    if obra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obra no encontrada")
    return obra


def _serializar_visita(visita: Visita) -> VisitaOut:
    return VisitaOut(
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
    )


@router.post("", response_model=VisitaOut, status_code=status.HTTP_201_CREATED)
async def registrar_visita(
    obra_id: int,
    descripcion: str | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)

    nueva_visita = Visita(obra_id=obra.id, usuario_id=usuario.id, descripcion=descripcion)
    db.add(nueva_visita)
    await db.flush()  # para obtener nueva_visita.id sin cerrar la transacción

    for archivo in archivos:
        try:
            subcarpeta = f"obras/{obra.id}/visitas/{nueva_visita.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + (archivo.filename or "").rsplit(".", 1)[-1]).lower()
        tipo = TipoArchivoVisita.VIDEO if extension in EXTENSIONES_VIDEO else TipoArchivoVisita.FOTO

        db.add(
            VisitaArchivo(
                visita_id=nueva_visita.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    await db.commit()

    result = await db.execute(select(Visita).where(Visita.id == nueva_visita.id))
    visita_completa = result.scalar_one()
    await db.refresh(visita_completa, attribute_names=["archivos"])
    return _serializar_visita(visita_completa)


@router.get("", response_model=list[VisitaOut])
async def listar_visitas(
    obra_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db),
):
    obra = await _obtener_obra_de_la_empresa(obra_id, empresa_id, db)
    result = await db.execute(
        select(Visita).where(Visita.obra_id == obra.id).order_by(Visita.fecha.desc())
    )
    visitas = result.scalars().all()
    salida = []
    for v in visitas:
        await db.refresh(v, attribute_names=["archivos"])
        salida.append(_serializar_visita(v))
    return salida
