from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timezone

from app.core.deps import get_current_user, require_inspector_or_higher, get_empresa_id
from app.database import get_db
from app.models.usuario import Usuario
from app.models.obra import Obra
from app.models.incidencia import Incidencia, HistorialIncidencia, EstadoIncidencia, TipoArchivoIncidencia, IncidenciaArchivo
from app.schemas.incidencia import IncidenciaResponse
from app.services.storage_service import guardar_archivo, ArchivoInvalido

router = APIRouter(prefix="/incidencias", tags=["Incidencias"])
obras_router = APIRouter(prefix="/obras", tags=["Incidencias"])


def _query_incidencias(empresa_id: int):
    return (
        select(Incidencia)
        .join(Obra)
        .where(Obra.usuario_id == empresa_id)
        .options(
            selectinload(Incidencia.responsable),
            selectinload(Incidencia.creador),
            selectinload(Incidencia.archivos),
            selectinload(Incidencia.tareas),
            selectinload(Incidencia.historial).selectinload(HistorialIncidencia.usuario)
        )
    )

@router.get("", response_model=list[IncidenciaResponse])
async def listar_todas_incidencias(
    estado: EstadoIncidencia | None = None,
    responsable_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id),
):
    query = _query_incidencias(empresa_id)
    if estado:
        query = query.where(Incidencia.estado == estado)
    if responsable_id:
        query = query.where(Incidencia.responsable_id == responsable_id)
        
    query = query.order_by(Incidencia.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@obras_router.get("/{obra_id}/incidencias", response_model=list[IncidenciaResponse])
async def listar_incidencias(
    obra_id: int,
    visita_id: int | None = None,
    estado: EstadoIncidencia | None = None,
    responsable_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(select(Obra).where(Obra.id == obra_id, Obra.usuario_id == empresa_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    query = _query_incidencias(empresa_id).where(Incidencia.obra_id == obra_id)
    if visita_id:
        query = query.where(Incidencia.visita_id == visita_id)
    if estado:
        query = query.where(Incidencia.estado == estado)
    if responsable_id:
        query = query.where(Incidencia.responsable_id == responsable_id)
        
    query = query.order_by(Incidencia.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def generar_codigo_incidencia(db: AsyncSession, empresa_id: int) -> str:
    # Cuenta global de incidencias en las obras de la empresa
    # Para ser exacto, deberíamos usar una secuencia, pero como solución sencilla consultamos count() o el último id.
    result = await db.execute(
        select(func.count(Incidencia.id))
        .join(Obra)
        .where(Obra.usuario_id == empresa_id)
    )
    count = result.scalar_one()
    return f"INC-{count + 1:03d}"


@obras_router.post("/{obra_id}/incidencias", response_model=IncidenciaResponse, status_code=status.HTTP_201_CREATED)
async def crear_incidencia(
    obra_id: int,
    titulo: str = Form(...),
    descripcion: str | None = Form(default=None),
    observaciones: str | None = Form(default=None),
    fecha_deteccion: date = Form(...),
    fecha_limite: date | None = Form(default=None),
    responsable_id: int | None = Form(default=None),
    estado: EstadoIncidencia = Form(default=EstadoIncidencia.NUEVA),
    visita_id: int | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(select(Obra).where(Obra.id == obra_id, Obra.usuario_id == empresa_id))
    obra = result.scalar_one_or_none()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    codigo = await generar_codigo_incidencia(db, empresa_id)
    
    fecha_resolucion = None
    if estado in [EstadoIncidencia.RESUELTA, EstadoIncidencia.CERRADA]:
        fecha_resolucion = date.today()

    nueva_incidencia = Incidencia(
        codigo=codigo,
        obra_id=obra_id,
        visita_id=visita_id,
        creador_id=usuario.id,
        responsable_id=responsable_id,
        titulo=titulo,
        descripcion=descripcion,
        observaciones=observaciones,
        fecha_deteccion=fecha_deteccion,
        fecha_limite=fecha_limite,
        fecha_resolucion=fecha_resolucion,
        estado=estado
    )
    
    db.add(nueva_incidencia)
    await db.flush()
    
    EXTENSIONES_VIDEO = {".mp4", ".mov"}
    for archivo in archivos:
        if not archivo.filename:
            continue
        try:
            subcarpeta = f"obras/{obra.id}/incidencias/{nueva_incidencia.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + archivo.filename.rsplit(".", 1)[-1]).lower()
        if extension in EXTENSIONES_VIDEO:
            tipo = TipoArchivoIncidencia.VIDEO
        elif extension in {".jpg", ".jpeg", ".png", ".webp"}:
            tipo = TipoArchivoIncidencia.FOTO
        else:
            tipo = TipoArchivoIncidencia.DOCUMENTO

        db.add(
            IncidenciaArchivo(
                incidencia_id=nueva_incidencia.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    historial = HistorialIncidencia(
        incidencia_id=nueva_incidencia.id,
        usuario_id=usuario.id,
        estado_anterior=None,
        estado_nuevo=nueva_incidencia.estado
    )
    db.add(historial)
    await db.commit()

    result = await db.execute(_query_incidencias(empresa_id).where(Incidencia.id == nueva_incidencia.id))
    return result.scalar_one()


@router.get("/{incidencia_id}", response_model=IncidenciaResponse)
async def obtener_incidencia(
    incidencia_id: int,
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(_query_incidencias(empresa_id).where(Incidencia.id == incidencia_id))
    incidencia = result.scalar_one_or_none()
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incidencia


@router.patch("/{incidencia_id}", response_model=IncidenciaResponse)
async def actualizar_incidencia(
    incidencia_id: int,
    titulo: str | None = Form(default=None),
    descripcion: str | None = Form(default=None),
    observaciones: str | None = Form(default=None),
    fecha_deteccion: date | None = Form(default=None),
    fecha_limite: date | None = Form(default=None),
    responsable_id: int | None = Form(default=None),
    estado: EstadoIncidencia | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(_query_incidencias(empresa_id).where(Incidencia.id == incidencia_id))
    incidencia = result.scalar_one_or_none()
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    estado_anterior = incidencia.estado
    cambio_estado = estado is not None and estado != estado_anterior

    if titulo is not None:
        incidencia.titulo = titulo
    if descripcion is not None:
        incidencia.descripcion = descripcion
    if observaciones is not None:
        incidencia.observaciones = observaciones
    if fecha_deteccion is not None:
        incidencia.fecha_deteccion = fecha_deteccion
    if fecha_limite is not None:
        incidencia.fecha_limite = fecha_limite
    if responsable_id is not None:
        incidencia.responsable_id = responsable_id
        
    if estado is not None:
        incidencia.estado = estado
        if estado in [EstadoIncidencia.RESUELTA, EstadoIncidencia.CERRADA] and estado_anterior not in [EstadoIncidencia.RESUELTA, EstadoIncidencia.CERRADA]:
            incidencia.fecha_resolucion = date.today()
        elif estado not in [EstadoIncidencia.RESUELTA, EstadoIncidencia.CERRADA]:
            incidencia.fecha_resolucion = None

    db.add(incidencia)
    
    EXTENSIONES_VIDEO = {".mp4", ".mov"}
    for archivo in archivos:
        if not archivo.filename:
            continue
        try:
            subcarpeta = f"obras/{incidencia.obra_id}/incidencias/{incidencia.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + archivo.filename.rsplit(".", 1)[-1]).lower()
        if extension in EXTENSIONES_VIDEO:
            tipo = TipoArchivoIncidencia.VIDEO
        elif extension in {".jpg", ".jpeg", ".png", ".webp"}:
            tipo = TipoArchivoIncidencia.FOTO
        else:
            tipo = TipoArchivoIncidencia.DOCUMENTO

        db.add(
            IncidenciaArchivo(
                incidencia_id=incidencia.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    if cambio_estado:
        historial = HistorialIncidencia(
            incidencia_id=incidencia.id,
            usuario_id=usuario.id,
            estado_anterior=estado_anterior,
            estado_nuevo=incidencia.estado
        )
        db.add(historial)
        
    await db.commit()
    
    result = await db.execute(_query_incidencias(empresa_id).where(Incidencia.id == incidencia_id))
    return result.scalar_one()


@router.delete("/{incidencia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_incidencia(
    incidencia_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(select(Incidencia).join(Obra).where(Incidencia.id == incidencia_id, Obra.usuario_id == empresa_id))
    incidencia = result.scalar_one_or_none()
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    
    await db.delete(incidencia)
    await db.commit()
