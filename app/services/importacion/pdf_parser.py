import os
import re
import pdfplumber
from app.services.importacion.models import (
    ResultadoAnalisis, MetadatosPresupuesto, CapituloIntermedio,
    PartidaIntermedia, ColumnMapping, LineaMedicionIntermedia
)

def parse_float(value: str) -> float:
    if not value:
        return 0.0
    val_str = str(value).strip().lower()
    val_str = re.sub(r'[€%]', '', val_str).strip()
    
    if '.' in val_str and ',' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        parts = val_str.split(',')
        if len(parts) == 2 and len(parts[1]) != 3:
            val_str = val_str.replace(',', '.')
        elif len(parts) == 2 and len(parts[1]) == 3:
            val_str = val_str.replace(',', '.')
            
    try:
        return float(val_str)
    except ValueError:
        return 0.0

async def analizar_pdf(file_path: str) -> ResultadoAnalisis:
    try:
        pdf = pdfplumber.open(file_path)
    except Exception as e:
        raise ValueError(f"Error al abrir PDF: {str(e)}")

    capitulos = []
    stack = []
    
    partidas_ok = 0
    partidas_warning = 0
    partidas_error = 0
    importe_total = 0.0
    iva = 21.0
    
    # Restrictive Chapter Regex: Optional CAPITULO, then digits, then UPPERCASE text
    capitulo_regex = re.compile(r'^(?:CAP[IÍ]TULO\s+)?(\d{1,3}[\.\d]*)\s+([A-ZÁÉÍÓÚÑ\s\,\.\-]+)$')
    
    # 1. Standard format: 01.01 Descripcion m2 1 55.00€ 0.00% 55.00€
    partida_regex_std = re.compile(r'^([\w\.\-]+)\s+(.*?)\s+([a-zA-Z0-9]{1,5})\s+([\d,\.]+)\s+([\d,\.]+)\s*€?(?:\s+[\d,\.]+\s*%)?\s+([\d,\.]+)\s*€?$')
    # 2. DIAM format: P-805 Nueva Partida 1 ud 46,00 € 46,00 €
    partida_regex_diam = re.compile(r'^([\w\.\-]+)\s+(.*?)\s+([\d,\.]+)\s+([a-zA-Z0-9]{1,5})\s+([\d,\.]+)\s*€?\s+([\d,\.]+)\s*€?$')
    # 3. Strict Medicion Partida: Must start with 01.01 or similar (digit dot digit), then uppercase unit (M2, ML, UD), then text
    partida_regex_med = re.compile(r'^(\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)\s+([A-Z]{1,4}[0-9]?)\s+(.*?)$')
    
    # 4. Measurement line pattern
    # Looks like: [Comentario opcional] 2 3,15 15,00 0.30 28,35
    medicion_line_regex = re.compile(r'^(.*?)\s*([\d,\.]+)?\s*([\d,\.]+)?\s*([\d,\.]+)?\s*([\d,\.]+)?\s+([\d,\.]+)$')
    
    text_lines = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            text_lines.extend(text.split('\n'))
            
    row_idx = 0
    parsing_mediciones = False
    
    for line in text_lines:
        line = line.strip()
        if not line:
            continue
        row_idx += 1
        
        line_lower = line.lower()
        if "coste directo" in line_lower or ("total" in line_lower and "subtotal" not in line_lower):
            continue
        if "iva" in line_lower:
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', line_lower)
            if m:
                iva = float(m.group(1))
            continue
            
        # Ignore legal garbage or page headers
        if "página" in line_lower or "presupuesto" in line_lower or "nota:" in line_lower or "licencias municipales" in line_lower or "código resumen" in line_lower or "mediciones" in line_lower:
            continue
            
        if "UD LONG. ANCH. ALT." in line or "UDS LONGITUD ANCHURA ALTURA" in line:
            parsing_mediciones = True
            continue
            
        codigo, desc, unidad, cantidad, precio, descuento, importe = None, None, None, 0.0, 0.0, 0.0, 0.0
        is_partida = False
        
        m_diam = partida_regex_diam.match(line)
        m_std = partida_regex_std.match(line)
        m_med = partida_regex_med.match(line)
        
        if m_diam:
            codigo, desc, cant_str, unidad, precio_str, importe_str = m_diam.groups()
            cantidad = parse_float(cant_str)
            precio = parse_float(precio_str)
            importe = parse_float(importe_str)
            is_partida = True
        elif m_std:
            codigo, desc, unidad, cant_str, precio_str, importe_str = m_std.groups()
            cantidad = parse_float(cant_str)
            precio = parse_float(precio_str)
            importe = parse_float(importe_str)
            is_partida = True
        elif m_med:
            cod, un, descrip = m_med.groups()
            if len(cod) > 4 or '.' in cod:
                codigo, unidad, desc = cod, un, descrip
                cantidad, precio, importe = 0.0, 0.0, 0.0 # Will be populated by mediciones later
                is_partida = True
        
        if is_partida:
            parsing_mediciones = False # Reset
            if not stack:
                dummy = CapituloIntermedio(
                    codigo="01", nombre="Capítulo General", orden=1, partidas=[], subcapitulos=[]
                )
                setattr(dummy, '_level', 1)
                capitulos.append(dummy)
                stack.append(dummy)
                
            warnings = []
            status = "ok"
            calculated_importe = cantidad * precio * (1 - descuento/100)
            if importe == 0.0 and calculated_importe > 0:
                importe = calculated_importe
                
            if importe > 0:
                diff = abs(calculated_importe - importe)
                if diff > 0.01 * importe:
                    warnings.append(f"El importe ({importe:.2f}) no coincide con cantidad x precio x (1 - dto) ({calculated_importe:.2f})")
                    status = "warning"
                    partidas_warning += 1
                else:
                    partidas_ok += 1
            else:
                if precio == 0.0:
                    status = "warning"
                    warnings.append("Partida sin precio (mediciones ciegas)")
                    partidas_warning += 1
                else:
                    status = "error"
                    warnings.append("Falta cantidad o precio unitario, o su producto es cero")
                    partidas_error += 1
                
            partida = PartidaIntermedia(
                codigo=codigo, descripcion=desc, unidad=unidad, cantidad=cantidad,
                precio_unitario=precio, descuento_porcentaje=descuento, importe=importe,
                status=status, warnings=warnings, fila_origen=row_idx, lineas_medicion=[]
            )
            stack[-1].partidas.append(partida)
            importe_total += importe
            
        else:
            # Check Chapter
            match_cap = capitulo_regex.match(line)
            if match_cap and len(match_cap.group(2)) > 3:
                parsing_mediciones = False
                codigo, desc = match_cap.groups()
                    
                level = 1
                if codigo:
                    parts = [p for p in re.split(r'[.-]', codigo) if p.strip()]
                    if len(parts) > 0:
                        level = len(parts)
                        
                nuevo_cap = CapituloIntermedio(
                    codigo=codigo, nombre=desc, orden=0, partidas=[], subcapitulos=[]
                )
                setattr(nuevo_cap, '_level', level)
                
                while stack and getattr(stack[-1], '_level', 1) >= level:
                    stack.pop()
                    
                if not stack:
                    nuevo_cap.orden = len(capitulos) + 1
                    capitulos.append(nuevo_cap)
                else:
                    parent = stack[-1]
                    nuevo_cap.orden = len(parent.subcapitulos) + 1
                    parent.subcapitulos.append(nuevo_cap)
                    
                stack.append(nuevo_cap)
                continue
                
            # If we are inside a partida and it's a measurement line
            if stack and stack[-1].partidas:
                last_partida = stack[-1].partidas[-1]
                
                # Check if it's a measurement line
                if parsing_mediciones or (re.search(r'[\d,\.]+\s+[\d,\.]+$', line) and len(re.findall(r'\d+', line)) >= 3):
                    # We might have a measurement line!
                    parts = re.split(r'\s+', line)
                    # A measurement line typically has text at start (optional), then up to 4 numbers, then a total
                    # Let's extract numbers from the end
                    nums = []
                    text_parts = []
                    for p in reversed(parts):
                        # try parse float
                        val = parse_float(p)
                        if val > 0 or p == '0' or p == '0.00' or p == '0,00':
                            nums.insert(0, val)
                        else:
                            # Not a number, everything before this is text
                            idx = parts.index(p)
                            text_parts = parts[:idx+1]
                            break
                    
                    if len(nums) >= 2: # At least one dimension and subtotal
                        subtotal = nums[-1]
                        dims = nums[:-1]
                        
                        u = dims[0] if len(dims) > 0 else None
                        l = dims[1] if len(dims) > 1 else None
                        a = dims[2] if len(dims) > 2 else None
                        h = dims[3] if len(dims) > 3 else None
                        
                        comentario = " ".join(text_parts).strip()
                        if len(comentario) < 2: comentario = None
                        
                        lm = LineaMedicionIntermedia(
                            comentario=comentario,
                            unidades=u,
                            longitud=l,
                            anchura=a,
                            altura=h,
                            subtotal=subtotal
                        )
                        last_partida.lineas_medicion.append(lm)
                        continue
                        
                # If we get here, it's just extra text. Append to description or observaciones.
                if line.isupper() and len(line) > 10:
                    pass # Ignore random uppercase garbage if it didn't match chapter
                else:
                    if not last_partida.observaciones:
                        last_partida.observaciones = line
                    else:
                        last_partida.observaciones += " " + line

    pdf.close()
    
    metadatos = MetadatosPresupuesto(
        nombre_obra=os.path.basename(file_path),
        iva=iva
    )
    
    def count_partidas(caps):
        return sum(len(c.partidas) + count_partidas(c.subcapitulos) for c in caps)

    total_partidas = count_partidas(capitulos)
    
    return ResultadoAnalisis(
        metadatos=metadatos,
        capitulos=capitulos,
        column_mapping=ColumnMapping(),
        total_capitulos=len(capitulos),
        total_partidas=total_partidas,
        partidas_ok=partidas_ok,
        partidas_warning=partidas_warning,
        partidas_error=partidas_error,
        importe_total_detectado=importe_total,
        warnings_globales=[],
        columnas_excel=[]
    )
