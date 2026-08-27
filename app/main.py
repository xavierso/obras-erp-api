"""
Punto de entrada de la API.

Ejecutar en desarrollo con:
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.routers import (
    auth,
    citas,
    dashboard,
    documentos,
    documentos_globales,
    equipo,
    informes,
    obras,
    perfil,
    visitas,
    visitas_globales,
    visitas_potenciales,
    tareas,
    incidencias,
)
from app.services.scheduler_service import detener_scheduler, iniciar_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asegura que exista la carpeta de almacenamiento local.
    Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    # El esquema de la base de datos se gestiona con Alembic (ver alembic/
    # y README) — NO se usa create_all aquí a propósito, para no chocar
    # con las migraciones (lección aprendida a las malas en la Fase A).

    iniciar_scheduler()
    yield
    detener_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: orígenes configurables vía ALLOWED_ORIGINS en .env (ver config.py).
# "*" por defecto para desarrollo. allow_credentials=False porque la app
# usa un Bearer token manual (Authorization header), no cookies — no hay
# necesidad de credenciales de navegador, y así se evita el conflicto de
# spec entre origen "*" y credenciales (los navegadores lo rechazan).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router)
app.include_router(obras.router)
app.include_router(visitas.router)
app.include_router(visitas_globales.router)
app.include_router(documentos.router)
app.include_router(documentos_globales.router)
app.include_router(perfil.router)
app.include_router(informes.router)
app.include_router(citas.router)
app.include_router(visitas_potenciales.router)
app.include_router(dashboard.router)
app.include_router(equipo.router)
app.include_router(tareas.router)
app.include_router(tareas.obras_router)
app.include_router(incidencias.router)
app.include_router(incidencias.obras_router)

# Sirve los archivos subidos (fotos, documentos, logos) en /files/...
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=settings.STORAGE_DIR), name="files")


@app.get("/", tags=["Salud"])
async def raiz():
    return {"status": "ok", "app": settings.APP_NAME}
