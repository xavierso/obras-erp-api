from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.core.deps import get_current_user, require_inspector_or_higher, get_empresa_id
from app.database import get_db
from app.models.usuario import Usuario
from app.models.obra import Obra
from app.models.tarea import Tarea, HistorialTarea, EstadoTarea, TipoArchivoTarea, TareaArchivo
from app.schemas.tarea import TareaCreate, TareaUpdate, TareaResponse, HistorialTareaResponse
from app.services.storage_service import guardar_archivo, ArchivoInvalido

router = APIRouter(prefix="/tareas", tags=["Tareas"])
obras_router = APIRouter(prefix="/obras", tags=["Tareas"])


@router.get("", response_model=list[TareaResponse])
async def listar_todas_tareas(
    estado: EstadoTarea | None = None,
    responsable_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
):
    query = (
        select(Tarea)
        .join(Obra)
        .where(Obra.empresa_id == empresa_id)
        .options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.archivos),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    
    if estado:
        query = query.where(Tarea.estado == estado)
    if responsable_id:
        query = query.where(Tarea.responsable_id == responsable_id)
        
    query = query.order_by(Tarea.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@obras_router.get("/{obra_id}/tareas", response_model=list[TareaResponse])
async def listar_tareas(
    obra_id: int,
    visita_id: int | None = None,
    estado: EstadoTarea | None = None,
    responsable_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(select(Obra).where(Obra.id == obra_id, Obra.empresa_id == empresa_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    query = (
        select(Tarea)
        .where(Tarea.obra_id == obra_id)
        .options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.archivos),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    
    if visita_id:
        query = query.where(Tarea.visita_id == visita_id)
    if estado:
        query = query.where(Tarea.estado == estado)
    if responsable_id:
        query = query.where(Tarea.responsable_id == responsable_id)
        
    query = query.order_by(Tarea.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@obras_router.post("/{obra_id}/tareas", response_model=TareaResponse, status_code=status.HTTP_201_CREATED)
async def crear_tarea(
    obra_id: int,
    titulo: str = Form(...),
    descripcion: str | None = Form(default=None),
    fecha_limite: date | None = Form(default=None),
    responsable_id: int | None = Form(default=None),
    estado: EstadoTarea = Form(default=EstadoTarea.PENDIENTE),
    visita_id: int | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(select(Obra).where(Obra.id == obra_id, Obra.empresa_id == empresa_id))
    obra = result.scalar_one_or_none()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    nueva_tarea = Tarea(
        obra_id=obra_id,
        empresa_id=empresa_id,
        visita_id=visita_id,
        creador_id=usuario.id,
        responsable_id=responsable_id,
        titulo=titulo,
        descripcion=descripcion,
        fecha_limite=fecha_limite,
        estado=estado
    )
    
    db.add(nueva_tarea)
    await db.flush()
    
    # Manejar archivos
    EXTENSIONES_VIDEO = {".mp4", ".mov"}
    for archivo in archivos:
        if not archivo.filename:
            continue
        try:
            subcarpeta = f"obras/{obra.id}/tareas/{nueva_tarea.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + archivo.filename.rsplit(".", 1)[-1]).lower()
        if extension in EXTENSIONES_VIDEO:
            tipo = TipoArchivoTarea.VIDEO
        elif extension in {".jpg", ".jpeg", ".png", ".webp"}:
            tipo = TipoArchivoTarea.FOTO
        else:
            tipo = TipoArchivoTarea.DOCUMENTO

        db.add(
            TareaArchivo(
                tarea_id=nueva_tarea.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    # Crear historial inicial
    historial = HistorialTarea(
        tarea_id=nueva_tarea.id,
        usuario_id=usuario.id,
        estado_anterior=None,
        estado_nuevo=nueva_tarea.estado
    )
    db.add(historial)
    await db.commit()

    result = await db.execute(
        select(Tarea).where(Tarea.id == nueva_tarea.id).options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.archivos),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    return result.scalar_one()


@router.get("/{tarea_id}", response_model=TareaResponse)
async def obtener_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(
        select(Tarea).join(Obra).where(Tarea.id == tarea_id, Obra.empresa_id == empresa_id).options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.archivos),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea


@router.patch("/{tarea_id}", response_model=TareaResponse)
async def actualizar_tarea(
    tarea_id: int,
    titulo: str | None = Form(default=None),
    descripcion: str | None = Form(default=None),
    fecha_limite: date | None = Form(default=None),
    responsable_id: int | None = Form(default=None),
    estado: EstadoTarea | None = Form(default=None),
    archivos: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(
        select(Tarea).join(Obra).where(Tarea.id == tarea_id, Obra.empresa_id == empresa_id).options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    estado_anterior = tarea.estado
    cambio_estado = estado is not None and estado != estado_anterior

    if titulo is not None:
        tarea.titulo = titulo
    if descripcion is not None:
        tarea.descripcion = descripcion
    if fecha_limite is not None:
        tarea.fecha_limite = fecha_limite
    if responsable_id is not None:
        tarea.responsable_id = responsable_id
    if estado is not None:
        tarea.estado = estado

    db.add(tarea)
    
    # Añadir nuevos archivos si se envían
    EXTENSIONES_VIDEO = {".mp4", ".mov"}
    for archivo in archivos:
        if not archivo.filename:
            continue
        try:
            subcarpeta = f"obras/{tarea.obra_id}/tareas/{tarea.id}"
            ruta_relativa, nombre_original = await guardar_archivo(archivo, subcarpeta)
        except ArchivoInvalido as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        extension = ("." + archivo.filename.rsplit(".", 1)[-1]).lower()
        if extension in EXTENSIONES_VIDEO:
            tipo = TipoArchivoTarea.VIDEO
        elif extension in {".jpg", ".jpeg", ".png", ".webp"}:
            tipo = TipoArchivoTarea.FOTO
        else:
            tipo = TipoArchivoTarea.DOCUMENTO

        db.add(
            TareaArchivo(
                tarea_id=tarea.id,
                tipo=tipo,
                ruta_archivo=ruta_relativa,
                nombre_original=nombre_original,
            )
        )

    if cambio_estado:
        historial = HistorialTarea(
            tarea_id=tarea.id,
            usuario_id=usuario.id,
            estado_anterior=estado_anterior,
            estado_nuevo=tarea.estado
        )
        db.add(historial)
        
    await db.commit()
    
    result = await db.execute(
        select(Tarea).where(Tarea.id == tarea_id).options(
            selectinload(Tarea.responsable),
            selectinload(Tarea.creador),
            selectinload(Tarea.archivos),
            selectinload(Tarea.historial).selectinload(HistorialTarea.usuario)
        )
    )
    return result.scalar_one()


@router.delete("/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tarea(
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_inspector_or_higher),
    empresa_id: int = Depends(get_empresa_id),
):
    result = await db.execute(
        select(Tarea).join(Obra).where(Tarea.id == tarea_id, Obra.empresa_id == empresa_id)
    )
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
    if tarea.visita_id is not None:
        raise HTTPException(status_code=400, detail="No se puede eliminar una tarea generada durante una visita. Cáncelala o complétala para mantener la trazabilidad.")
        
    await db.delete(tarea)
    await db.commit()
