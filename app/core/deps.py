"""
Dependency de FastAPI que extrae y valida el usuario autenticado
a partir del header 'Authorization: Bearer <token>'.

Cualquier endpoint que necesite estar protegido simplemente declara:
    usuario: Usuario = Depends(get_current_user)
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.usuario import RolUsuario, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    usuario_id = decode_access_token(token)
    if usuario_id is None:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()

    if usuario is None or not usuario.is_active:
        raise credentials_exception

    return usuario


async def get_empresa_id(usuario: Usuario = Depends(get_current_user)) -> int:
    """
    Devuelve el id que identifica la "empresa" a la que pertenecen las
    obras: el propio id si es admin, o el admin_id si es inspector.

    Todos los routers que listan/consultan obras (y lo que cuelga de
    ellas) deben filtrar por este id en vez de por usuario.id directo,
    para que admin e inspectores del mismo equipo vean las mismas obras.
    """
    if usuario.rol == RolUsuario.ADMIN:
        return usuario.id
    if usuario.admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta de inspector no está vinculada a ninguna empresa",
        )
    return usuario.admin_id


async def require_admin(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Para endpoints reservados solo a administradores (gestión de obras,
    documentos, citas, perfil, dashboard, informes, equipo). Los
    inspectores reciben 403 al intentar usarlos.
    """
    if usuario.rol != RolUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción solo está disponible para administradores",
        )
    return usuario
