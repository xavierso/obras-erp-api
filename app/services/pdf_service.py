"""
Generación de informes PDF, migrado desde bot_erp_obras/services/pdf_service.py.

Conserva la identidad visual del bot:
- Portada a sangre completa con una foto real de la obra (elegida al azar
  entre las visitas), degradado oscuro inferior, nombre de la empresa
  superpuesto en blanco espaciado, y línea de acento en el color de marca.
  Si la obra no tiene fotos, se genera un plano arquitectónico abstracto
  de respaldo.
- Cronología con cada visita numerada, en dos columnas: observaciones a la
  izquierda, cuadrícula de fotos a la derecha con pie de foto, recortadas
  a tamaño uniforme.

Diferencia respecto al bot: las imágenes ya no se descargan de Telegram al
vuelo, se leen directamente del almacenamiento local (storage_service).
"""
import io
import random
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
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
DPI_PORTADA = 150
COLOR_MARCA_DEFECTO = "#1E3A5F"

FOTOS_POR_VISITA_EN_GRID = 4
LADO_MINIATURA_MM = 28


# --------------------------------------------------------------------------
# Utilidades de color
# --------------------------------------------------------------------------
def _hex_a_rgb(color_hex: str) -> tuple[int, int, int]:
    color_hex = color_hex.lstrip("#")
    return tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))  # noqa: E203


def _hex_a_reportlab_color(color_hex: str) -> colors.Color:
    r, g, b = _hex_a_rgb(color_hex)
    return colors.Color(r / 255, g / 255, b / 255)


# --------------------------------------------------------------------------
# Portada
# --------------------------------------------------------------------------
def _elegir_foto_random(visitas: list[Visita]) -> Path | None:
    candidatas = []
    for visita in visitas:
        for archivo in visita.archivos:
            if archivo.tipo == TipoArchivoVisita.FOTO:
                ruta = STORAGE_ROOT / archivo.ruta_archivo
                if ruta.exists():
                    candidatas.append(ruta)
    return random.choice(candidatas) if candidatas else None


def _generar_plano_abstracto(ancho_px: int, alto_px: int, color_hex: str) -> PILImage.Image:
    """
    Respaldo cuando la obra aún no tiene fotos: un plano arquitectónico
    abstracto generado por código (líneas finas estilo blueprint).
    """
    fondo = (13, 22, 35)  # azul marino oscuro
    lineas = (90, 130, 160)  # azul claro, estilo plano

    img = PILImage.new("RGB", (ancho_px, alto_px), fondo)
    draw = ImageDraw.Draw(img)

    paso = max(ancho_px // 18, 30)
    for x in range(0, ancho_px, paso):
        draw.line([(x, 0), (x, alto_px)], fill=lineas, width=1)
    for y in range(0, alto_px, paso):
        draw.line([(0, y), (ancho_px, y)], fill=lineas, width=1)

    # Un par de "muros" gruesos para sugerir planta arquitectónica.
    accent = _hex_a_rgb(color_hex)
    margen = int(ancho_px * 0.12)
    draw.rectangle(
        [margen, int(alto_px * 0.25), ancho_px - margen, int(alto_px * 0.75)],
        outline=accent,
        width=4,
    )
    draw.line(
        [(ancho_px // 2, int(alto_px * 0.25)), (ancho_px // 2, int(alto_px * 0.75))],
        fill=accent,
        width=3,
    )
    return img


def _preparar_imagen_portada(ruta_foto: Path | None, color_hex: str) -> PILImage.Image:
    ancho_px = int(PAGE_W / 72 * DPI_PORTADA)
    alto_px = int(PAGE_H / 72 * DPI_PORTADA)

    if ruta_foto is not None:
        base = PILImage.open(ruta_foto).convert("RGB")
        # "cover fit": recorta al centro manteniendo proporción del lienzo.
        ratio_destino = ancho_px / alto_px
        ratio_origen = base.width / base.height
        if ratio_origen > ratio_destino:
            nuevo_alto = alto_px
            nuevo_ancho = int(ratio_origen * nuevo_alto)
        else:
            nuevo_ancho = ancho_px
            nuevo_alto = int(nuevo_ancho / ratio_origen)
        base = base.resize((nuevo_ancho, nuevo_alto))
        x0 = (nuevo_ancho - ancho_px) // 2
        y0 = (nuevo_alto - alto_px) // 2
        base = base.crop((x0, y0, x0 + ancho_px, y0 + alto_px))
    else:
        base = _generar_plano_abstracto(ancho_px, alto_px, color_hex)

    base = base.convert("RGBA")

    # Degradado oscuro en el tercio inferior, para que el texto blanco
    # se lea bien encima de cualquier foto.
    degradado = PILImage.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(degradado)
    inicio_y = int(alto_px * 0.55)
    for y in range(inicio_y, alto_px):
        progreso = (y - inicio_y) / (alto_px - inicio_y)
        alpha = int(210 * progreso)
        draw.line([(0, y), (ancho_px, y)], fill=(0, 0, 0, alpha))

    resultado = PILImage.alpha_composite(base, degradado)
    return resultado.convert("RGB")


def _dibujar_texto_espaciado(
    c: pdfcanvas.Canvas,
    texto: str,
    centro_x: float,
    y: float,
    font_name: str,
    font_size: float,
    espaciado: float,
    color=colors.white,
) -> None:
    """Dibuja texto centrado con espaciado extra entre letras (tracking)."""
    c.setFont(font_name, font_size)
    ancho_total = sum(c.stringWidth(ch, font_name, font_size) + espaciado for ch in texto)
    ancho_total -= espaciado  # sin espaciado extra tras la última letra
    x = centro_x - ancho_total / 2
    c.setFillColor(color)
    for ch in texto:
        c.drawString(x, y, ch)
        x += c.stringWidth(ch, font_name, font_size) + espaciado


def _crear_portada_pdf(obra: Obra, nombre_empresa: str, color_hex: str, ruta_foto: Path | None) -> bytes:
    buffer = io.BytesIO()
    c = pdfcanvas.Canvas(buffer, pagesize=A4)

    imagen_fondo = _preparar_imagen_portada(ruta_foto, color_hex)
    c.drawImage(ImageReader(imagen_fondo), 0, 0, width=PAGE_W, height=PAGE_H)

    color_marca = _hex_a_reportlab_color(color_hex)
    margen = 20 * mm

    # Línea de acento en el color de marca.
    c.setFillColor(color_marca)
    c.rect(margen, 48 * mm, PAGE_W - 2 * margen, 1.2 * mm, fill=1, stroke=0)

    # Nombre de la empresa, blanco, espaciado.
    _dibujar_texto_espaciado(
        c, nombre_empresa.upper(), PAGE_W / 2, 56 * mm, "Helvetica-Bold", 20, 3.2
    )

    # Datos de la obra.
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(PAGE_W / 2, 38 * mm, obra.nombre)

    c.setFont("Helvetica", 10)
    subtitulo = obra.codigo
    if obra.cliente:
        subtitulo += f"  ·  {obra.cliente}"
    c.drawCentredString(PAGE_W / 2, 31 * mm, subtitulo)

    c.showPage()
    c.save()
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Cronología (cuerpo del informe)
# --------------------------------------------------------------------------
def _miniatura_uniforme(ruta_archivo: Path, lado_px: int = 300) -> RLImage:
    """Recorta una foto a un cuadrado uniforme, para que la cuadrícula quede alineada."""
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

    celdas = []
    fila = []
    for foto in fotos[:FOTOS_POR_VISITA_EN_GRID]:
        fila.append(_miniatura_uniforme(foto))
        if len(fila) == 2:
            celdas.append(fila)
            fila = []
    if fila:
        celdas.append(fila)

    tabla = Table(celdas, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    if videos:
        nota = Paragraph(
            f"+ {len(videos)} vídeo(s) adjunto(s) — disponibles en la app.",
            ParagraphStyle("videonota", fontSize=7, textColor=colors.grey),
        )
        return Table([[tabla], [nota]], style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    return tabla


def _construir_cuerpo_pdf(obra: Obra, visitas: list[Visita], color_hex: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
    )

    color_marca = _hex_a_reportlab_color(color_hex)
    estilo_titulo = ParagraphStyle(
        "titulo", fontName="Helvetica-Bold", fontSize=14, textColor=color_marca, spaceAfter=4
    )
    estilo_numero_visita = ParagraphStyle(
        "numvisita", fontName="Helvetica-Bold", fontSize=11, textColor=colors.black, spaceBefore=10
    )
    estilo_fecha = ParagraphStyle("fecha", fontName="Helvetica", fontSize=8, textColor=colors.grey)
    estilo_obs = ParagraphStyle(
        "obs", fontName="Helvetica", fontSize=9, textColor=colors.black, alignment=TA_LEFT, leading=12
    )

    elementos = [
        Paragraph("Cronología de visitas", estilo_titulo),
        Spacer(1, 4),
    ]

    if not visitas:
        elementos.append(Paragraph("Todavía no hay visitas registradas en esta obra.", estilo_obs))

    for i, visita in enumerate(visitas, start=1):
        elementos.append(Paragraph(f"Visita {i}", estilo_numero_visita))
        elementos.append(Paragraph(visita.fecha.strftime("%d/%m/%Y %H:%M"), estilo_fecha))

        texto_obs = visita.descripcion or "Sin observaciones registradas."
        columna_izquierda = Paragraph(texto_obs, estilo_obs)
        columna_derecha = _grid_fotos_visita(visita)

        fila = Table(
            [[columna_izquierda, columna_derecha]],
            colWidths=[(PAGE_W - 40 * mm) * 0.5, (PAGE_W - 40 * mm) * 0.5],
        )
        fila.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 8),
                ]
            )
        )
        elementos.append(fila)

        linea_separadora = Table([[""]], colWidths=[PAGE_W - 40 * mm], rowHeights=[0.5])
        linea_separadora.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey)]))
        elementos.append(Spacer(1, 6))
        elementos.append(linea_separadora)
        elementos.append(Spacer(1, 4))

    def _pie_de_pagina(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawRightString(
            PAGE_W - 20 * mm, 10 * mm, f"{obra.codigo} · Página {doc_obj.page}"
        )
        canvas_obj.restoreState()

    doc.build(elementos, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Combinar portada + cuerpo, y función pública
# --------------------------------------------------------------------------
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
) -> bytes:
    """Función pública: arma el informe completo (portada + cronología)."""
    nombre_empresa = nombre_empresa or "Mi Empresa"
    color_hex = color_principal or COLOR_MARCA_DEFECTO

    ruta_foto = _elegir_foto_random(visitas)
    portada = _crear_portada_pdf(obra, nombre_empresa, color_hex, ruta_foto)
    cuerpo = _construir_cuerpo_pdf(obra, visitas, color_hex)
    return _combinar_pdfs(portada, cuerpo)


# --------------------------------------------------------------------------
# Parte de trabajo (visita potencial, una sola página)
# --------------------------------------------------------------------------
def _espaciar_texto(texto: str, separador: str = "\u2009\u2009") -> str:
    """Mismo efecto de tracking que en la portada, pero como texto de Paragraph."""
    return separador.join(list(texto))


def generar_parte_trabajo_pdf(
    cita,
    visita_potencial,
    nombre_empresa: str | None,
    color_principal: str | None,
) -> bytes:
    """
    Genera el "parte de trabajo": documento de una sola página para una
    visita potencial (sin obra formal todavía), con la misma línea visual
    que el informe completo pero condensada.

    `cita` es una CitaVisita y `visita_potencial` una VisitaPotencial;
    no se importan sus tipos aquí para evitar un ciclo de imports —
    basta con que tengan los atributos usados abajo (duck typing).
    """
    nombre_empresa = nombre_empresa or "Mi Empresa"
    color_hex = color_principal or COLOR_MARCA_DEFECTO
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
