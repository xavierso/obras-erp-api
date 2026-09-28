"""
Endpoints de autenticación.

POST /auth/register  -> crea un usuario nuevo
POST /auth/login      -> devuelve un token JWT (form-data: username, password)
GET  /auth/me         -> devuelve el usuario autenticado actual (requiere token)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.invitacion import EstadoInvitacion, Invitacion
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import Token
from app.schemas.equipo import AceptarInvitacionRequest
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


from app.models.empresa import Empresa

@router.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(datos: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == datos.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese email",
        )

    nueva_empresa = Empresa(nombre=f"Empresa de {datos.nombre}")
    db.add(nueva_empresa)
    await db.flush()

    import secrets
    from app.services.email_service import enviar_email
    token_verificacion = secrets.token_urlsafe(32)

    nuevo_usuario = Usuario(
        email=datos.email,
        nombre=datos.nombre,
        hashed_password=hash_password(datos.password),
        rol=RolUsuario.ADMIN,
        empresa_id=nueva_empresa.id,
        email_verificado=False,
        token_verificacion=token_verificacion
    )
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)

    # Enviar correo de verificación
    asunto = "Confirma tu cuenta en Obras ERP"
    # En desarrollo esto apuntará al frontend localhost o donde esté alojado
    enlace_verificacion = f"http://localhost:3000/confirmar?token={token_verificacion}"
    html = f"""
    <h2>¡Hola {datos.nombre}!</h2>
    <p>Gracias por registrarte en Obras ERP.</p>
    <p>Por favor, haz clic en el siguiente enlace para confirmar tu cuenta y acceder al sistema:</p>
    <p><a href="{enlace_verificacion}">Confirmar mi cuenta</a></p>
    <br/>
    <p>Si el botón no funciona, puedes copiar y pegar este enlace en tu navegador:</p>
    <p>{enlace_verificacion}</p>
    """
    await enviar_email(datos.email, asunto, html)

    return nuevo_usuario


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2PasswordRequestForm usa "username", aquí lo tratamos como email.
    result = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    usuario = result.scalar_one_or_none()

    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if usuario is None or not verify_password(form_data.password, usuario.hashed_password):
        raise credenciales_invalidas

    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    # if not usuario.email_verificado:
    #     raise HTTPException(status_code=403, detail="Por favor, verifica tu correo electrónico antes de iniciar sesión.")

    token = create_access_token(usuario.id)
    return Token(access_token=token)


@router.get("/me", response_model=UsuarioOut)
async def perfil_propio(usuario: Usuario = Depends(get_current_user)):
    return usuario


@router.post("/aceptar-invitacion", response_model=Token, status_code=status.HTTP_201_CREATED)
async def aceptar_invitacion(datos: AceptarInvitacionRequest, db: AsyncSession = Depends(get_db)):
    """
    El inspector llega aquí con el token que le mandó su admin. Crea su
    cuenta ya vinculada (rol=INSPECTOR, empresa_id=el que lo invitó), y
    devuelve el token de acceso directo.
    """
    result = await db.execute(select(Invitacion).where(Invitacion.token == datos.token))
    invitacion = result.scalar_one_or_none()

    if invitacion is None or invitacion.estado != EstadoInvitacion.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitación no válida o ya utilizada",
        )
    if invitacion.expira_at < datetime.now(timezone.utc):
        invitacion.estado = EstadoInvitacion.EXPIRADA
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitación caducada")

    result = await db.execute(select(Usuario).where(Usuario.email == invitacion.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese email",
        )

    nuevo_usuario = Usuario(
        email=invitacion.email,
        nombre=datos.nombre,
        hashed_password=hash_password(datos.password),
        rol=invitacion.rol,
        empresa_id=invitacion.empresa_id,
        email_verificado=True,
    )
    db.add(nuevo_usuario)
    invitacion.estado = EstadoInvitacion.ACEPTADA
    await db.commit()
    await db.refresh(nuevo_usuario)

    token = create_access_token(nuevo_usuario.id)
    return Token(access_token=token)

from pydantic import BaseModel

class ConfirmarRequest(BaseModel):
    token: str

@router.post("/confirmar", status_code=status.HTTP_200_OK)
async def confirmar_email(datos: ConfirmarRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.token_verificacion == datos.token))
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado")

    if usuario.email_verificado:
        return {"mensaje": "La cuenta ya estaba verificada"}

    usuario.email_verificado = True
    usuario.token_verificacion = None
    await db.commit()

    return {"mensaje": "Cuenta verificada con éxito"}
