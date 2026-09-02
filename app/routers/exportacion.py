import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as OpenpyxlImage

from app.core.deps import require_director, get_current_user, get_empresa_id
from app.database import get_db
from app.models.obra import Obra
from app.models.presupuesto import Presupuesto, CapituloPresupuesto
from app.models.incidencia import Incidencia
from app.models.tarea import Tarea
from app.models.usuario import Usuario
from app.models.invitacion import Invitacion, EstadoInvitacion
from app.models.empresa import Empresa

router = APIRouter(prefix="/exportar", tags=["Exportación"])

def apply_header_style(cell, color_principal: str = None):
    # DIAM Style Header
    fill_color = "151513" # Dark Gray
    text_color = "C8B89C" # Gold Accent
    
    cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
    cell.font = Font(color=text_color, bold=True, name="Montserrat", size=10)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    
    border_color = "8A8975"
    thin = Side(border_style="thin", color=border_color)
    cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)

def insert_company_header(ws, title: str, perfil: Empresa):
    ws.merge_cells('A1:D1')
    ws['A1'] = (perfil.nombre if perfil else "DIAM - GESTIÓN DE OBRAS").upper()
    ws['A1'].font = Font(size=14, bold=True, name="Space Grotesk", color="151513")
    ws['A1'].alignment = Alignment(horizontal="left", vertical="center")
    
    ws.merge_cells('A2:D2')
    ws['A2'] = title.upper()
    ws['A2'].font = Font(size=11, italic=False, name="Montserrat", color="8A8975", bold=True)
    
    # Add a visual separator line
    for col in range(1, 8):
        cell = ws.cell(row=3, column=col)
        cell.border = Border(bottom=Side(border_style="medium", color="C8B89C"))
        
    return 5

@router.get("/excel")
async def export_to_excel(
    admin: Usuario = Depends(require_director),
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id)
):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    perfil = result.scalar_one_or_none()
    color_principal = perfil.color_principal if perfil else "#1E3A5F"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    # 1. Presupuestos
    ws_pres = wb.create_sheet(title="Presupuestos")
    start_row = insert_company_header(ws_pres, "Listado de Presupuestos", perfil)
    
    headers = ["Código", "Nombre", "Monto", "Estado"]
    for col, h in enumerate(headers, 1):
        cell = ws_pres.cell(row=start_row, column=col, value=h)
        apply_header_style(cell, color_principal)
        
    result_pres = await db.execute(
        select(Presupuesto).options(selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas)).where(Presupuesto.empresa_id == empresa_id)
    )
    presupuestos = result_pres.scalars().all()
    
    for i, p in enumerate(presupuestos, start=start_row + 1):
        ws_pres.cell(row=i, column=1, value=p.codigo or "")
        ws_pres.cell(row=i, column=2, value=p.nombre)
        cell_monto = ws_pres.cell(row=i, column=3, value=p.total)
        cell_monto.number_format = '#,##0.00 €'
        ws_pres.cell(row=i, column=4, value=p.estado.value.upper() if p.estado else "")
    
    # 2. Obras
    ws_obras = wb.create_sheet(title="Obras")
    start_row = insert_company_header(ws_obras, "Listado de Obras", perfil)
    
    headers_obras = ["Código", "Nombre", "Cliente", "Estado"]
    for col, h in enumerate(headers_obras, 1):
        cell = ws_obras.cell(row=start_row, column=col, value=h)
        apply_header_style(cell, color_principal)
        
    result_obras = await db.execute(select(Obra).where(Obra.empresa_id == empresa_id))
    obras = result_obras.scalars().all()
    
    for i, o in enumerate(obras, start=start_row + 1):
        ws_obras.cell(row=i, column=1, value=o.codigo)
        ws_obras.cell(row=i, column=2, value=o.nombre)
        ws_obras.cell(row=i, column=3, value=o.cliente or "")
        ws_obras.cell(row=i, column=4, value=o.estado.value.upper() if o.estado else "")

    # 3. Incidencias
    ws_inc = wb.create_sheet(title="Incidencias")
    start_row = insert_company_header(ws_inc, "Listado de Incidencias", perfil)
    
    headers_inc = ["Código", "Título", "Obra", "Estado"]
    for col, h in enumerate(headers_inc, 1):
        cell = ws_inc.cell(row=start_row, column=col, value=h)
        apply_header_style(cell, color_principal)
        
    result_inc = await db.execute(select(Incidencia).options(selectinload(Incidencia.obra)).where(Incidencia.empresa_id == empresa_id))
    incidencias = result_inc.scalars().all()
    
    for i, inc in enumerate(incidencias, start=start_row + 1):
        ws_inc.cell(row=i, column=1, value=inc.codigo)
        ws_inc.cell(row=i, column=2, value=inc.titulo)
        ws_inc.cell(row=i, column=3, value=inc.obra.nombre if inc.obra else "")
        ws_inc.cell(row=i, column=4, value=inc.estado.value.upper() if inc.estado else "")

    # 4. Tareas
    ws_tar = wb.create_sheet(title="Tareas")
    start_row = insert_company_header(ws_tar, "Listado de Tareas", perfil)
    
    headers_tar = ["Título", "Obra", "Fecha Límite", "Estado"]
    for col, h in enumerate(headers_tar, 1):
        cell = ws_tar.cell(row=start_row, column=col, value=h)
        apply_header_style(cell, color_principal)
        
    result_tar = await db.execute(select(Tarea).options(selectinload(Tarea.obra)).where(Tarea.empresa_id == empresa_id))
    tareas = result_tar.scalars().all()
    
    for i, tar in enumerate(tareas, start=start_row + 1):
        ws_tar.cell(row=i, column=1, value=tar.titulo)
        ws_tar.cell(row=i, column=2, value=tar.obra.nombre if tar.obra else "")
        ws_tar.cell(row=i, column=3, value=tar.fecha_limite.strftime("%Y-%m-%d") if tar.fecha_limite else "")
        ws_tar.cell(row=i, column=4, value=tar.estado.value.upper() if tar.estado else "")

    # 5. Personal
    ws_pers = wb.create_sheet(title="Personal")
    start_row = insert_company_header(ws_pers, "Listado de Personal", perfil)
    
    headers_pers = ["Nombre / Email", "Rol", "Estado"]
    for col, h in enumerate(headers_pers, 1):
        cell = ws_pers.cell(row=start_row, column=col, value=h)
        apply_header_style(cell, color_principal)
        
    result_act = await db.execute(
        select(Usuario).where(Usuario.empresa_id == empresa_id)
    )
    activos = result_act.scalars().all()
    
    row_idx = start_row + 1
    for u in activos:
        ws_pers.cell(row=row_idx, column=1, value=u.nombre)
        ws_pers.cell(row=row_idx, column=2, value=u.rol.value)
        ws_pers.cell(row=row_idx, column=3, value="ACTIVO")
        row_idx += 1
        
    result_pend = await db.execute(
        select(Invitacion).where(
            Invitacion.empresa_id == empresa_id,
            Invitacion.estado == EstadoInvitacion.PENDIENTE
        )
    )
    pendientes = result_pend.scalars().all()
    
    for p in pendientes:
        ws_pers.cell(row=row_idx, column=1, value=p.email)
        ws_pers.cell(row=row_idx, column=2, value=p.rol.value if p.rol else "")
        ws_pers.cell(row=row_idx, column=3, value="PENDIENTE")
        row_idx += 1

    for ws in wb.worksheets:
        for col in ws.columns:
            max_length = 0
            column = openpyxl.utils.get_column_letter(col[0].column)
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column].width = min(adjusted_width, 40)
            
    if perfil and perfil.logo_ruta and os.path.exists(perfil.logo_ruta):
        for ws in wb.worksheets:
            try:
                # We need PIL to get image dimensions properly if possible, but OpenpyxlImage does it.
                img = OpenpyxlImage(perfil.logo_ruta)
                # Max height 60
                ratio = 60 / img.height if img.height > 0 else 1
                img.height = int(img.height * ratio)
                img.width = int(img.width * ratio)
                ws.add_image(img, 'E1')
            except Exception:
                pass

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
    empresa_str = perfil.nombre.replace(' ', '_') if perfil else 'Datos'
    filename = f"Exportacion_{empresa_str}_{fecha_str}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/excel/presupuesto/{presupuesto_id}")
async def export_single_presupuesto(
    presupuesto_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    empresa_id: int = Depends(get_empresa_id)
):
    # Fetch Presupuesto with chapters and items
    result = await db.execute(
        select(Presupuesto)
        .options(selectinload(Presupuesto.capitulos).selectinload(CapituloPresupuesto.partidas))
        .where(Presupuesto.id == presupuesto_id, Presupuesto.empresa_id == empresa_id)
    )
    presupuesto = result.scalar_one_or_none()
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado o no autorizado")
        
    result_perfil = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    perfil = result_perfil.scalar_one_or_none()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Presupuesto"
    
    # Turn off gridlines
    ws.sheet_view.showGridLines = False
    
    # Colors
    bg_dark = "151513"
    gold = "C8B89C"
    white = "FFFFFF"
    gray = "8A8975"
    light_bg = "E8EBF2" # Very light blue/gray as in image
    blue_text = "0F427E" # Like the reference image for values
    
    # 1. Top Header (Rows 1-4)
    fill_dark = PatternFill(start_color=bg_dark, end_color=bg_dark, fill_type="solid")
    for row in range(1, 5):
        for col in range(1, 9):
            ws.cell(row=row, column=col).fill = fill_dark
            
    ws.cell(row=2, column=2, value="PRESUPUESTO").font = Font(color=white, size=18, bold=True, name="Arial")
    ws.cell(row=3, column=2, value=perfil.nombre if perfil else "DIAM - Empresa").font = Font(color=gold, size=12, bold=True, name="Arial")
    
    dir_str = perfil.direccion if perfil and perfil.direccion else "Dirección no especificada"
    ws.cell(row=4, column=2, value=dir_str).font = Font(color=gray, size=9, name="Arial")
    
    ws.cell(row=2, column=6, value="Presupuesto #:").font = Font(color=gray, size=9, name="Arial")
    ws.cell(row=2, column=7, value=presupuesto.codigo or f"PRE-{presupuesto.id}").font = Font(color=gold, size=9, bold=True, name="Arial")
    ws.cell(row=2, column=7).alignment = Alignment(horizontal="right")
    
    from datetime import datetime, timedelta
    ws.cell(row=3, column=6, value="Fecha:").font = Font(color=gray, size=9, name="Arial")
    ws.cell(row=3, column=7, value=datetime.now().strftime("%d/%m/%Y")).font = Font(color=gold, size=9, bold=True, name="Arial")
    ws.cell(row=3, column=7).alignment = Alignment(horizontal="right")
    
    ws.cell(row=4, column=6, value="Válido hasta:").font = Font(color=gray, size=9, name="Arial")
    valid_until = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
    ws.cell(row=4, column=7, value=valid_until).font = Font(color=gold, size=9, bold=True, name="Arial")
    ws.cell(row=4, column=7).alignment = Alignment(horizontal="right")
    
    # 2. Client and Project Info
    border_gold_bottom = Border(bottom=Side(border_style="medium", color=gold))
    
    ws.cell(row=6, column=2, value="PREPARADO PARA").font = Font(color=gray, size=10, bold=True, name="Arial")
    ws.cell(row=6, column=2).border = border_gold_bottom
    ws.cell(row=6, column=3).border = border_gold_bottom
    ws.cell(row=6, column=4).border = border_gold_bottom
    
    ws.cell(row=6, column=6, value="DETALLES DEL PROYECTO").font = Font(color=gray, size=10, bold=True, name="Arial")
    ws.cell(row=6, column=6).border = border_gold_bottom
    ws.cell(row=6, column=7).border = border_gold_bottom
    
    # Client
    ws.cell(row=7, column=2, value="Cliente:").font = Font(bold=True, size=9, name="Arial")
    ws.cell(row=7, column=3, value=presupuesto.cliente_nombre or "No especificado").font = Font(color=blue_text, size=9, name="Arial")
    
    ws.cell(row=8, column=2, value="Dirección:").font = Font(bold=True, size=9, name="Arial")
    ws.cell(row=8, column=3, value=presupuesto.direccion or "No especificada").font = Font(color=blue_text, size=9, name="Arial")
    
    # Project
    ws.cell(row=7, column=6, value="Proyecto:").font = Font(bold=True, size=9, name="Arial")
    ws.cell(row=7, column=7, value=presupuesto.nombre).font = Font(color=blue_text, size=9, name="Arial")
    
    # 3. Table Header
    current_row = 11
    headers = ["#", "Descripción", "Unidad", "Cantidad", "Precio Unitario", "Desc. %", "Importe"]
    
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=current_row, column=col, value=h)
        c.fill = PatternFill(start_color="334D7A", end_color="334D7A", fill_type="solid") # Dark blue like image
        c.font = Font(color=white, bold=True, name="Arial", size=10)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(left=Side(style='thin', color=white), right=Side(style='thin', color=white))
        
    current_row += 1
    
    # 4. Table Body
    fill_light = PatternFill(start_color=light_bg, end_color=light_bg, fill_type="solid")
    font_bold = Font(bold=True, name="Arial", size=9, color="334D7A") # Dark blue bold for chapter titles
    font_normal = Font(name="Arial", size=9, color="000000")
    font_blue = Font(name="Arial", size=9, color=blue_text)
    
    border_thin = Border(
        left=Side(style='thin', color="D3D3D3"),
        right=Side(style='thin', color="D3D3D3"),
        bottom=Side(style='thin', color="D3D3D3"),
        top=Side(style='thin', color="D3D3D3")
    )
    
    for cap_idx, cap in enumerate(presupuesto.capitulos, 1):
        # Chapter
        for col in range(1, 8):
            c = ws.cell(row=current_row, column=col)
            c.fill = fill_light
            c.border = border_thin
            
        ws.cell(row=current_row, column=2, value=cap.nombre.upper()).font = font_bold
        ws.cell(row=current_row, column=2).alignment = Alignment(horizontal="left")
        current_row += 1
        
        # Partidas
        for p_idx, partida in enumerate(cap.partidas, 1):
            for col in range(1, 8):
                ws.cell(row=current_row, column=col).border = border_thin
                
            ws.cell(row=current_row, column=1, value=p_idx).font = font_normal
            ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")
            
            ws.cell(row=current_row, column=2, value=partida.descripcion).font = font_normal
            
            ws.cell(row=current_row, column=3, value=partida.unidad).font = font_normal
            ws.cell(row=current_row, column=3).alignment = Alignment(horizontal="center")
            
            ws.cell(row=current_row, column=4, value=partida.cantidad).font = font_blue
            ws.cell(row=current_row, column=4).alignment = Alignment(horizontal="center")
            
            c_precio = ws.cell(row=current_row, column=5, value=partida.precio_unitario)
            c_precio.font = font_blue
            c_precio.number_format = '#,##0.00 €'
            
            c_desc = ws.cell(row=current_row, column=6, value=partida.descuento_porcentaje)
            c_desc.font = font_blue
            c_desc.number_format = '0.00"%"'
            c_desc.alignment = Alignment(horizontal="center")
            
            c_imp = ws.cell(row=current_row, column=7, value=partida.importe)
            c_imp.font = font_normal
            c_imp.number_format = '#,##0.00 €'
            
            current_row += 1
            
    # 5. Totals
    current_row += 1
    
    thick_top = Border(top=Side(style='thick', color="000000"))
    
    ws.cell(row=current_row, column=6, value="Coste Directo:").font = font_bold
    ws.cell(row=current_row, column=6).border = thick_top
    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="right")
    
    c_sub = ws.cell(row=current_row, column=7, value=presupuesto.coste_directo)
    c_sub.font = font_bold
    c_sub.number_format = '#,##0.00 €'
    c_sub.border = thick_top
    current_row += 1
    
    ws.cell(row=current_row, column=6, value=f"IVA ({presupuesto.iva}%):").font = font_bold
    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="right")
    c_iva = ws.cell(row=current_row, column=7, value=presupuesto.importe_iva)
    c_iva.font = font_bold
    c_iva.number_format = '#,##0.00 €'
    current_row += 1
    
    thick_top_bottom = Border(top=Side(style='thick', color="000000"), bottom=Side(style='thick', color="000000"))
    ws.cell(row=current_row, column=6, value="TOTAL:").font = Font(bold=True, size=11, name="Arial")
    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="right")
    ws.cell(row=current_row, column=6).border = thick_top_bottom
    
    c_tot = ws.cell(row=current_row, column=7, value=presupuesto.total)
    c_tot.font = Font(bold=True, size=11, name="Arial")
    c_tot.number_format = '#,##0.00 €'
    c_tot.border = thick_top_bottom
    
    current_row += 3
    
    # 6. Notes
    ws.cell(row=current_row, column=2, value="NOTAS Y CONDICIONES").font = Font(bold=True, size=10, name="Arial")
    ws.cell(row=current_row, column=2).border = border_gold_bottom
    ws.cell(row=current_row, column=3).border = border_gold_bottom
    ws.cell(row=current_row, column=4).border = border_gold_bottom
    ws.cell(row=current_row, column=5).border = border_gold_bottom
    current_row += 1
    
    ws.cell(row=current_row, column=2, value="1. Este presupuesto es válido por 30 días.").font = font_normal
    current_row += 1
    ws.cell(row=current_row, column=2, value="2. Condiciones de pago: A convenir.").font = font_normal
    
    # Adjust widths
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 45
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 15
    
    # Optional: Logo
    if perfil and perfil.logo_ruta and os.path.exists(perfil.logo_ruta):
        try:
            img = OpenpyxlImage(perfil.logo_ruta)
            ratio = 50 / img.height if img.height > 0 else 1
            img.height = int(img.height * ratio)
            img.width = int(img.width * ratio)
            ws.add_image(img, 'B2') # Adding near title
        except Exception:
            pass
            
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"Presupuesto_{presupuesto.codigo or presupuesto.id}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
