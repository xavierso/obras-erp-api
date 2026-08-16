"""
Registro de visitas potenciales y generación del "parte de trabajo" en PDF.
Restringido a admins, igual que citas.py (del que depende).
"""
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.database import get_db
from app.models.cita_visita import CitaVisita
from app.models.perfil_empresa import PerfilEmpresa
from app.models.usuario import Usuario
from app.models.visita import TipoArchivoVisita
from app.models.visita_potencial import VisitaPotencial, VisitaPotencialArchivo
from app.schemas.visita_potencial import VisitaPotencialOut
from app.services.pdf_service import generar_parte_trabajo_pdf
from app.services.storage_service import ArchivoInvalido, guardar_archivo, url_publica

router = APIRouter(prefix="/citas/{cita_id}/visitas-potenciales", tags=["Visitas Potenciales"])

EXTENSIONES_VIDEO = {".mp4", ".mov"}


async def _obtener_cita_de_la_empresa(cita_id: int, admin: Usuario, db: AsyncSession) -> CitaVisita:
    result = await db.execute(
        select(CitaVisita).where(CitaVisita.id == cita_id, CitaVisita.usuario_id == admin.id)
    )
    cita = result.scalar_one_or_none()
    if cita is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return cita


async def _obtener_visita_potencial_de_la_empresa(
    cita_id: int, visita_potencial_id: int, admin: Usuario, db: AsyncSession
) -> VisitaPotencial:
    await _obtener_cita_de_la_empresa(cita_id, admin, db)
    result = await db.execute(
        select(VisitaPotencial).where(
            VisitaPotencial.id == visita_potencial_id,
            VisitaPotencial.cita_id == cita_id,
        )
    )
    visita = result.scalar_one_or_none()
    if visita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visita potencial no encontrada"
        )
    return visita


def _serializar_visita_potencial(visita: VisitaPotencial) -> VisitaPotencialOut:
    return VisitaPotencialOut(
        id=visita.id,
        cita_id=visita.cita_id,
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


@router.post("", response_model=VisitaPotencialOut, status_code=status.HTTP_201_CREATED)
async def registrar_visita_potencial(
    cita_id: int,
    descripcion: str | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, admin, db)

    nueva_visita = VisitaPotencial(cita_id=cita.id, usuario_id=admin.id, descripcion=descripcion)
    db.add(nueva_visita)
    await db.flush()

    for archivo in archivos:
        try:
            subcarpeta = f"citas/{cita.id}/visitas-potenciales/{nueva_visita.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + (archivo.filename or "").rsplit(".", 1)[-1]).lower()
        tipo = TipoArchivoVisita.VIDEO if extension in EXTENSIONES_VIDEO else TipoArchivoVisita.FOTO

        db.add(
            VisitaPotencialArchivo(
                visita_potencial_id=nueva_visita.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    await db.commit()

    result = await db.execute(
        select(VisitaPotencial).where(VisitaPotencial.id == nueva_visita.id)
    )
    visita_completa = result.scalar_one()
    await db.refresh(visita_completa, attribute_names=["archivos"])
    return _serializar_visita_potencial(visita_completa)


@router.get("", response_model=list[VisitaPotencialOut])
async def listar_visitas_potenciales(
    cita_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, admin, db)
    result = await db.execute(
        select(VisitaPotencial)
        .where(VisitaPotencial.cita_id == cita.id)
        .order_by(VisitaPotencial.fecha.desc())
    )
    visitas = result.scalars().all()
    salida = []
    for v in visitas:
        await db.refresh(v, attribute_names=["archivos"])
        salida.append(_serializar_visita_potencial(v))
    return salida


@router.get("/{visita_potencial_id}/parte-trabajo")
async def generar_parte_de_trabajo(
    cita_id: int,
    visita_potencial_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cita = await _obtener_cita_de_la_empresa(cita_id, admin, db)
    visita = await _obtener_visita_potencial_de_la_empresa(cita_id, visita_potencial_id, admin, db)
    await db.refresh(visita, attribute_names=["archivos"])

    result = await db.execute(
        select(PerfilEmpresa).where(PerfilEmpresa.usuario_id == admin.id)
    )
    perfil = result.scalar_one_or_none()

    pdf_bytes = generar_parte_trabajo_pdf(
        cita=cita,
        visita_potencial=visita,
        nombre_empresa=perfil.nombre_empresa if perfil else None,
        color_principal=perfil.color_principal if perfil else None,
    )

    nombre_archivo = f"parte_trabajo_cita_{cita.id}_visita_{visita.id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
