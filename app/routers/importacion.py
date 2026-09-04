from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.deps import get_current_user, get_empresa_id
from app.models.usuario import Usuario
from app.services.importacion.excel_parser import analizar_excel
from app.services.importacion.pdf_parser import analizar_pdf
from app.services.importacion.models import ResultadoAnalisis
from app.services.presupuesto_service import crear_presupuesto, get_presupuesto, crear_capitulo, actualizar_presupuesto
from app.schemas.presupuesto import PresupuestoCreate, PresupuestoOut, CapituloPresupuestoCreate, PartidaPresupuestoCreate, PresupuestoUpdate
import tempfile
import os
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/importar", tags=["Importación"])

class CapituloConfirmacion(BaseModel):
    nombre: str
    orden: int
    partidas: list[dict] = []
    subcapitulos: list['CapituloConfirmacion'] = []

class ConfirmarImportacion(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    cliente_nombre: Optional[str] = None
    direccion: Optional[str] = None
    iva: float = 21.0
    obra_id: Optional[int] = None
    archivo_origen: Optional[str] = None
    target_id: Optional[int] = None
    capitulos: List[CapituloConfirmacion]

@router.post("/presupuesto/analizar", response_model=ResultadoAnalisis)
async def analizar_presupuesto_endpoint(
    file: UploadFile = File(...),
    usuario: Usuario = Depends(get_current_user)
):
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(('.xlsx', '.xls', '.pdf')):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Debe ser .xlsx, .xls o .pdf")
        
    ext = os.path.splitext(file.filename)[1]
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(temp_fd, 'wb') as f:
            content = await file.read()
            f.write(content)
            
        if filename_lower.endswith('.pdf'):
            resultado = await analizar_pdf(temp_path)
        else:
            resultado = await analizar_excel(temp_path)
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno durante el análisis: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/presupuesto/confirmar", response_model=PresupuestoOut)
async def confirmar_importacion_endpoint(
    data: ConfirmarImportacion,
    usuario: Usuario = Depends(get_current_user),
    empresa_id: int = Depends(get_empresa_id),
    db: AsyncSession = Depends(get_db)
):
    try:
        observaciones_nuevas = f"Importado desde: {data.archivo_origen}" if data.archivo_origen else "Importado"

        from app.models.presupuesto import CapituloPresupuesto, PartidaPresupuesto, EstadoPresupuesto, Presupuesto
        from app.services.presupuesto_service import get_presupuesto

        if data.target_id:
            presupuesto_db = await get_presupuesto(db, data.target_id, empresa_id)
            if not presupuesto_db:
                raise HTTPException(status_code=404, detail="Presupuesto destino no encontrado")
                
            obs_actuales = presupuesto_db.observaciones or ""
            presupuesto_db.observaciones = f"{obs_actuales}\n{observaciones_nuevas}".strip()
            presupuesto_id = data.target_id
        else:
            # Crear nuevo presupuesto
            from sqlalchemy import select, desc
            from datetime import datetime, timezone
            
            año_actual = datetime.now(timezone.utc).year
            prefijo = f"PTO-{año_actual}-"
            result = await db.execute(select(Presupuesto.codigo).where(Presupuesto.codigo.like(f"{prefijo}%")).order_by(desc(Presupuesto.codigo)).limit(1))
            ultimo_codigo = result.scalar_one_or_none()
            nuevo_numero = 1
            if ultimo_codigo:
                try: nuevo_numero = int(ultimo_codigo.split("-")[-1]) + 1
                except ValueError: pass
            
            presupuesto_db = Presupuesto(
                codigo=f"{prefijo}{nuevo_numero:03d}",
                nombre=data.nombre,
                descripcion=data.descripcion,
                cliente_nombre=data.cliente_nombre,
                direccion=data.direccion,
                iva=data.iva,
                obra_id=data.obra_id,
                observaciones=observaciones_nuevas,
                estado=EstadoPresupuesto.BORRADOR,
                creador_id=usuario.id,
                empresa_id=empresa_id
            )
            db.add(presupuesto_db)
            await db.flush()
            presupuesto_id = presupuesto_db.id

        # Función recursiva para insertar capítulos y partidas
        async def insertar_capitulos(capitulos: List[CapituloConfirmacion], padre_id: Optional[int] = None):
            for cap in capitulos:
                capitulo_db = CapituloPresupuesto(
                    nombre=cap.nombre,
                    orden=cap.orden,
                    padre_id=padre_id,
                    presupuesto_id=presupuesto_id
                )
                db.add(capitulo_db)
                await db.flush() # para obtener capitulo_db.id

                for p in cap.partidas:
                    partida_db = PartidaPresupuesto(
                        codigo=p.get('codigo', ''),
                        descripcion=p.get('descripcion', ''),
                        unidad=p.get('unidad', 'ud'),
                        cantidad=float(p.get('cantidad', 1.0)),
                        precio_unitario=float(p.get('precio_unitario', 0.0)),
                        descuento_porcentaje=float(p.get('descuento_porcentaje', 0.0)),
                        capitulo_id=capitulo_db.id,
                        observaciones=p.get('observaciones')
                    )
                    db.add(partida_db)
                    await db.flush() # Para poder asignar el id de partida a las lineas
                    
                    lineas = p.get('lineas_medicion')
                    if lineas and isinstance(lineas, list):
                        from app.models.presupuesto import LineaMedicion
                        for lm in lineas:
                            linea_db = LineaMedicion(
                                partida_id=partida_db.id,
                                comentario=lm.get('comentario'),
                                unidades=lm.get('unidades'),
                                longitud=lm.get('longitud'),
                                anchura=lm.get('anchura'),
                                altura=lm.get('altura')
                            )
                            db.add(linea_db)
                    
                if cap.subcapitulos:
                    await insertar_capitulos(cap.subcapitulos, capitulo_db.id)

        await insertar_capitulos(data.capitulos)
        await db.commit()
        
        return await get_presupuesto(db, presupuesto_id, empresa_id)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al confirmar la importación: {str(e)}")
