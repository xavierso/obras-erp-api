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

    try:
        usuario_id = decode_access_token(token)
        if usuario_id is None:
            raise credentials_exception

        result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
        usuario = result.scalar_one_or_none()

        if usuario is None or not usuario.is_active:
            raise credentials_exception

        return usuario
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e


async def get_empresa_id(usuario: Usuario = Depends(get_current_user)) -> int:
    """
    Devuelve el id que identifica la "empresa" a la que pertenecen las
    obras: el propio id si es admin, o el admin_id si es otro rol.
    """
    if usuario.rol == RolUsuario.ADMIN:
        return usuario.id
    if usuario.admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no está vinculada a ninguna empresa",
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


async def require_director(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Para endpoints accesibles por ADMIN y DIRECTOR (gestión de obras, citas, informes).
    """
    if usuario.rol not in (RolUsuario.ADMIN, RolUsuario.DIRECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de Administrador o Director",
        )
    return usuario


async def require_inspector_or_higher(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Para endpoints de registro de visitas (ADMIN, DIRECTOR, INSPECTOR).
    LECTOR queda excluido.
    """
    if usuario.rol not in (RolUsuario.ADMIN, RolUsuario.DIRECTOR, RolUsuario.INSPECTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de Inspector o superior",
        )
    return usuario
