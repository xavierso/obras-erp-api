"""
Servicio de almacenamiento de archivos.

Reemplaza el mecanismo del bot original (guardar file_id de Telegram sin
descargar nada). Aquí sí hay que guardar los bytes reales, porque no hay
servidores de Telegram detrás sirviendo las fotos.

Implementación actual: disco local, bajo STORAGE_DIR (por defecto ./storage).
Estructura: storage/obras/{obra_id}/visitas/{visita_id}/archivo.jpg
            storage/obras/{obra_id}/documentos/{categoria}/archivo.pdf
            storage/perfiles/{usuario_id}/logo.png

Si en el futuro se migra a S3/Cloudflare R2, solo hay que reemplazar las
funciones de este archivo (guardar_archivo / eliminar_archivo) manteniendo
la misma firma; el resto de la app no necesita cambios.
"""
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

STORAGE_ROOT = Path(settings.STORAGE_DIR)

# Límite de tamaño por archivo (en bytes). 25 MB por defecto.
MAX_FILE_SIZE = 25 * 1024 * 1024

EXTENSIONES_PERMITIDAS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",  # fotos
    ".mp4", ".mov",  # vídeos
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",  # documentos
}


class ArchivoInvalido(Exception):
    pass


async def guardar_archivo(archivo: UploadFile, subcarpeta: str) -> tuple[str, str]:
    """
    Guarda un UploadFile en disco bajo STORAGE_ROOT/subcarpeta/ con un nombre
    único, y devuelve (ruta_relativa, nombre_original).

    subcarpeta ejemplo: "obras/3/visitas/12" o "perfiles/1"
    """
    extension = Path(archivo.filename or "").suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ArchivoInvalido(f"Extensión no permitida: {extension or '(sin extensión)'}")

    contenido = await archivo.read()
    if len(contenido) > MAX_FILE_SIZE:
        raise ArchivoInvalido("El archivo supera el tamaño máximo permitido (25 MB)")

    destino_dir = STORAGE_ROOT / subcarpeta
    destino_dir.mkdir(parents=True, exist_ok=True)

    nombre_unico = f"{uuid.uuid4().hex}{extension}"
    destino_path = destino_dir / nombre_unico

    with open(destino_path, "wb") as f:
        f.write(contenido)

    ruta_relativa = str(destino_path.relative_to(STORAGE_ROOT)).replace("\\", "/")
    return ruta_relativa, (archivo.filename or nombre_unico)


def eliminar_archivo(ruta_relativa: str) -> None:
    """Borra un archivo del disco si existe. No lanza error si ya no está."""
    path = STORAGE_ROOT / ruta_relativa
    if path.exists():
        path.unlink()


def url_publica(ruta_relativa: str) -> str:
    """Construye la URL pública servida por FastAPI (ver mount en main.py)."""
    return f"/files/{ruta_relativa}"
