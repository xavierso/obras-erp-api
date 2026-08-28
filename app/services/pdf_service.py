import io
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import Image as RLImage
from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.models.obra import Obra
from app.models.visita import TipoArchivoVisita, Visita

STORAGE_ROOT = Path(settings.STORAGE_DIR)
PAGE_W, PAGE_H = A4

FOTOS_POR_VISITA_EN_GRID = 4
LADO_MINIATURA_MM = 35

ASSETS_DIR = Path(__file__).parent.parent / "assets"
WATERMARK_PATH = ASSETS_DIR / "watermark_body_light.png"
ISOMETRIC_BG_PATH = ASSETS_DIR / "isometric_bg.jpg"

def _hex_a_rgb(color_hex: str) -> tuple[int, int, int]:
    color_hex = color_hex.lstrip("#")
    return tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))

def _hex_a_reportlab_color(color_hex: str) -> colors.Color:
    r, g, b = _hex_a_rgb(color_hex)
    return colors.Color(r / 255, g / 255, b / 255)


# --------------------------------------------------------------------------
# Portada
# --------------------------------------------------------------------------
def _crear_portada_pdf(obra: Obra, nombre_empresa: str, num_visitas: int, logo_ruta: str | None = None) -> bytes:
    buffer = io.BytesIO()
    c = pdfcanvas.Canvas(buffer, pagesize=A4)
    c.saveState()

    # Center faded image
    if WATERMARK_PATH.exists():
        c.drawImage(str(WATERMARK_PATH), PAGE_W*0.15, PAGE_H*0.25, width=PAGE_W*0.7, height=PAGE_H*0.5, mask='auto', preserveAspectRatio=True)

    # Top Card
    p_empresa = ParagraphStyle('empresa', fontName='Helvetica-Bold', fontSize=14, alignment=TA_RIGHT)
    company_name = Paragraph(nombre_empresa.upper(), p_empresa)
    
    logo = ''
    if logo_ruta:
        ruta_completa = STORAGE_ROOT / logo_ruta
        if ruta_completa.exists():
            try:
                logo = RLImage(str(ruta_completa), width=40*mm, height=15*mm, kind='proportional')
            except:
                pass

    top_card = Table([[logo, company_name]], colWidths=[PAGE_W*0.4, PAGE_W*0.4], rowHeights=[20*mm])
    top_card.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 5*mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 5*mm),
    ]))
    top_card.wrapOn(c, PAGE_W, PAGE_H)
    top_card.drawOn(c, PAGE_W*0.1, PAGE_H - 30*mm)

    # Title
    c.setFont('Helvetica-Bold', 40)
    c.drawString(20*mm, 100*mm, 'INFORME DE')
    c.drawString(20*mm, 85*mm, 'VISITA DE OBRA')
    c.setFont('Helvetica', 14)
    c.drawString(20*mm, 75*mm, 'SEGUIMIENTO Y CONTROL DE OBRA')

    # Data Table
    style_label = '<font size=7 color=grey>'
    style_val = '<font size=9><b>'
    p_style = ParagraphStyle('t', fontName='Helvetica', leading=12)
    p_center = ParagraphStyle('c', fontName='Helvetica', alignment=TA_CENTER, leading=12)

    fecha_emision = datetime.now().strftime('%d/%m/%Y')
    cliente = obra.cliente or "Sin especificar"
    
    def basic_cell(label, val):
        return Paragraph(f'{style_label}{label}</font><br/>{style_val}{val}</b></font>', p_style)

    data = [
        [
            basic_cell('NOMBRE DE LA OBRA', (obra.nombre or "")[:35]),
            basic_cell('FECHA DE EMISIÓN', fecha_emision),
            Paragraph(f'{style_label}CÓDIGO DE OBRA</font><br/>{style_val}{obra.codigo or ""}</b></font>', p_center)
        ],
        [
            basic_cell('DIRECCIÓN', (obra.direccion or "")[:40]),
            basic_cell('CLIENTE', cliente[:35]),
            Paragraph(f'{style_label}VISITAS REGISTRADAS</font><br/><font size=12><b>{num_visitas}</b></font>', p_center)
        ]
    ]

    total_w = PAGE_W - 40*mm
    t = Table(data, colWidths=[total_w*0.4, total_w*0.35, total_w*0.25], rowHeights=[15*mm, 15*mm])
    t.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5*mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 5*mm),
        ('ALIGN', (2,0), (2,1), 'CENTER'),
    ]))

    t.wrapOn(c, PAGE_W, PAGE_H)
    t.drawOn(c, 20*mm, 30*mm)

    # Footer
    fecha_generacion = datetime.now().strftime('%d/%m/%Y a las %H:%M')
    c.setFont('Helvetica', 8)
    c.drawCentredString(PAGE_W/2, 15*mm, f'Informe generado el {fecha_generacion}')

    c.restoreState()
    c.showPage()
    c.save()
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Cronología (cuerpo del informe)
# --------------------------------------------------------------------------
def _miniatura_uniforme(ruta_archivo: Path, lado_px: int = 400) -> RLImage:
    img = PILImage.open(ruta_archivo).convert("RGB")
    lado_menor = min(img.width, img.height)
    x0 = (img.width - lado_menor) // 2
    y0 = (img.height - lado_menor) // 2
    img = img.crop((x0, y0, x0 + lado_menor, y0 + lado_menor)).resize((lado_px, lado_px))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    lado_pt = LADO_MINIATURA_MM * mm
    return RLImage(buf, width=lado_pt, height=lado_pt)

def _grid_fotos_visita(visita: Visita) -> Table | Paragraph:
    fotos = [
        STORAGE_ROOT / a.ruta_archivo
        for a in visita.archivos
        if a.tipo == TipoArchivoVisita.FOTO and (STORAGE_ROOT / a.ruta_archivo).exists()
    ]
    videos = [a for a in visita.archivos if a.tipo == TipoArchivoVisita.VIDEO]

    if not fotos and not videos:
        return Paragraph("Sin fotos adjuntas.", ParagraphStyle("sinfotos", fontSize=8, textColor=colors.grey))

    # Construir celdas con la foto y el subtitulo "Foto X. \n Fecha"
    celdas = []
    fila = []
    fecha_str = visita.fecha.strftime("%d/%m/%Y")
    
    style_caption = ParagraphStyle('cap', fontName='Helvetica-Bold', fontSize=7, alignment=TA_CENTER, spaceBefore=4)
    style_date = ParagraphStyle('date', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=colors.grey)
    
    for idx, foto in enumerate(fotos[:FOTOS_POR_VISITA_EN_GRID]):
        img_rl = _miniatura_uniforme(foto)
        p_caption = Paragraph(f"Foto {idx+1}.", style_caption)
        p_date = Paragraph(fecha_str, style_date)
        
        cell_table = Table([[img_rl], [p_caption], [p_date]], colWidths=[LADO_MINIATURA_MM * mm])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        
        fila.append(cell_table)
        if len(fila) == 2:
            celdas.append(fila)
            fila = []
            
    if fila:
        celdas.append(fila)

    tabla = Table(celdas, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))

    if videos:
        nota = Paragraph(
            f"+ {len(videos)} vídeo(s) adjunto(s) — disponibles en la app.",
            ParagraphStyle("videonota", fontSize=7, textColor=colors.grey),
        )
        return Table([[tabla], [nota]], style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    return tabla

def _construir_cuerpo_pdf(obra: Obra, visitas: list[Visita]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    def draw_header_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        
        # Marca de agua
        if WATERMARK_PATH.exists():
            canvas_obj.drawImage(str(WATERMARK_PATH), PAGE_W*0.1, 0, width=PAGE_W*0.9, height=PAGE_H*0.8, mask='auto', preserveAspectRatio=True, anchor='s')
        
        # Cabecera
        canvas_obj.setFont('Helvetica-Bold', 10)
        canvas_obj.drawString(15*mm, PAGE_H - 15*mm, 'Integración de Servicios de Construcción y Rehabilitación')
        canvas_obj.drawRightString(PAGE_W - 15*mm, PAGE_H - 15*mm, (obra.direccion or obra.nombre).upper())
        canvas_obj.setLineWidth(1)
        canvas_obj.line(15*mm, PAGE_H - 17*mm, PAGE_W - 15*mm, PAGE_H - 17*mm)
        
        # Pie
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(15*mm, 20*mm, PAGE_W - 15*mm, 20*mm)
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.drawString(15*mm, 15*mm, f'Informe {obra.codigo}')
        fecha_gen = datetime.now().strftime('%d/%m/%Y a las %H:%M')
        canvas_obj.drawCentredString(PAGE_W/2, 15*mm, f'Informe generado el {fecha_gen}')
        canvas_obj.drawRightString(PAGE_W - 15*mm, 15*mm, f'Página {doc_obj.page}')
        
        # Linea vertical central
        canvas_obj.setStrokeColor(colors.lightgrey)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(PAGE_W*0.43, 25*mm, PAGE_W*0.43, PAGE_H - 25*mm)
        
        canvas_obj.restoreState()

    left_style = ParagraphStyle('Left', fontName='Helvetica', fontSize=9, leading=12)
    right_title = ParagraphStyle('RightTitle', fontName='Helvetica-Bold', fontSize=10, spaceAfter=10)
    box_style = ParagraphStyle('Box', fontName='Helvetica-Bold', fontSize=12, textColor=colors.white, alignment=TA_CENTER)
    
    elementos = []
    
    if not visitas:
        elementos.append(Paragraph("Todavía no hay visitas registradas en esta obra.", left_style))
    
    for i, visita in enumerate(visitas, start=1):
        left_content = []
        
        # Numero de visita en recuadro negro
        num_str = f"{i:02d}"
        t_box = Table([ [Paragraph(num_str, box_style)] ], colWidths=[12*mm], rowHeights=[12*mm])
        t_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), colors.black),
            ('VALIGN', (0,0), (0,0), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
        ]))
        left_content.append(t_box)
        left_content.append(Spacer(1, 10))
        
        left_content.append(Paragraph(f'<b>VISITA {num_str}</b>', left_style))
        left_content.append(Spacer(1, 5))
        left_content.append(Paragraph(f'<b>{visita.fecha.strftime("%d/%m/%Y")}</b>', left_style))
        left_content.append(Spacer(1, 10))
        
        autor = getattr(visita, "usuario", None)
        autor_nombre = autor.nombre_completo if autor else "Desconocido"
        left_content.append(Paragraph(f'<font color="grey">Registrado por: {autor_nombre}</font>', left_style))
        left_content.append(Spacer(1, 10))
        
        texto_obs = visita.descripcion or "Sin observaciones registradas."
        left_content.append(Paragraph(texto_obs, left_style))
        
        right_content = []
        right_content.append(Paragraph('REPORTAJE FOTOGRÁFICO', right_title))
        right_content.append(_grid_fotos_visita(visita))
        
        col_w_left = PAGE_W*0.43 - 15*mm
        col_w_right = PAGE_W*0.57 - 15*mm
        
        main_table = Table([[left_content, right_content]], colWidths=[col_w_left, col_w_right])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (0,0), 8*mm),
            ('LEFTPADDING', (1,0), (1,0), 8*mm),
        ]))
        
        elementos.append(main_table)
        elementos.append(Spacer(1, 15*mm))
        
        # Linea separadora horizontal
        line_separator = Table([['']], colWidths=[PAGE_W - 30*mm])
        line_separator.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey)]))
        elementos.append(line_separator)
        elementos.append(Spacer(1, 10*mm))

    doc.build(elementos, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    return buffer.getvalue()


def _combinar_pdfs(portada_bytes: bytes, cuerpo_bytes: bytes) -> bytes:
    writer = PdfWriter()
    for lector_bytes in (portada_bytes, cuerpo_bytes):
        lector = PdfReader(io.BytesIO(lector_bytes))
        for pagina in lector.pages:
            writer.add_page(pagina)

    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()

def generar_informe_pdf(
    obra: Obra,
    visitas: list[Visita],
    nombre_empresa: str | None,
    color_principal: str | None,
    logo_ruta: str | None = None,
) -> bytes:
    nombre_empresa = nombre_empresa or "Mi Empresa"
    portada = _crear_portada_pdf(obra, nombre_empresa, len(visitas), logo_ruta)
    cuerpo = _construir_cuerpo_pdf(obra, visitas)
    return _combinar_pdfs(portada, cuerpo)


def _espaciar_texto(texto: str, separador: str = "\u2009\u2009") -> str:
    return separador.join(list(texto))

def generar_parte_trabajo_pdf(
    cita,
    visita_potencial,
    nombre_empresa: str | None,
    color_principal: str | None,
) -> bytes:
    nombre_empresa = nombre_empresa or "Mi Empresa"
    color_hex = color_principal or "#1E3A5F"
    color_marca = _hex_a_reportlab_color(color_hex)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=0,
        bottomMargin=16 * mm,
    )

    estilo_banda = ParagraphStyle(
        "banda", fontName="Helvetica-Bold", fontSize=15, textColor=colors.white, alignment=1
    )
    banda = Table(
        [[Paragraph(_espaciar_texto(nombre_empresa.upper()), estilo_banda)]],
        colWidths=[PAGE_W],
    )
    banda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color_marca),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )

    estilo_titulo = ParagraphStyle(
        "titulo_parte", fontName="Helvetica-Bold", fontSize=15, textColor=colors.black,
        spaceBefore=16, spaceAfter=4,
    )
    estilo_meta = ParagraphStyle(
        "meta_parte", fontName="Helvetica", fontSize=9, textColor=colors.grey, spaceAfter=10
    )
    estilo_obs = ParagraphStyle(
        "obs_parte", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=12
    )
    estilo_seccion = ParagraphStyle(
        "seccion_parte", fontName="Helvetica-Bold", fontSize=10, textColor=color_marca,
        spaceBefore=6, spaceAfter=4,
    )

    referencia = cita.nombre_referencia or (
        f"Obra #{cita.obra_id}" if cita.obra_id else "Sin referencia"
    )

    elementos = [banda, Spacer(1, 4)]
    elementos.append(Paragraph("Parte de trabajo", estilo_titulo))
    elementos.append(Paragraph(referencia, estilo_meta))
    elementos.append(
        Paragraph(
            f"Fecha de la visita: {visita_potencial.fecha.strftime('%d/%m/%Y %H:%M')}",
            estilo_meta,
        )
    )

    if getattr(cita, "notas", None):
        elementos.append(Paragraph("Notas de la cita", estilo_seccion))
        elementos.append(Paragraph(cita.notas, estilo_obs))

    elementos.append(Paragraph("Observaciones de la visita", estilo_seccion))
    elementos.append(
        Paragraph(visita_potencial.descripcion or "Sin observaciones registradas.", estilo_obs)
    )

    elementos.append(Paragraph("Fotografías", estilo_seccion))
    elementos.append(_grid_fotos_visita(visita_potencial))

    def _pie_de_pagina(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawRightString(
            PAGE_W - 20 * mm, 10 * mm, f"Generado el {datetime.now().strftime('%d/%m/%Y')}"
        )
        canvas_obj.restoreState()

    doc.build(elementos, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()
