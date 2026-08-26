import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.models.usuario import Usuario, RolUsuario
from app.models.invitacion import Invitacion, EstadoInvitacion
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

async def test_invitar_inspector_success(auth_client: AsyncClient, db_session: AsyncSession):
    response = await auth_client.post(
        "/equipo/invitar",
        json={"email": "nuevo@example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo@example.com"
    assert "token" in data
    assert data["estado"] == EstadoInvitacion.PENDIENTE.value
    
    # Verificar en DB
    result = await db_session.execute(select(Invitacion).where(Invitacion.email == "nuevo@example.com"))
    invitacion = result.scalar_one_or_none()
    assert invitacion is not None
    assert invitacion.email == "nuevo@example.com"


async def test_invitar_inspector_existing_user(auth_client: AsyncClient, db_session: AsyncSession):
    # Crear usuario existente
    user = Usuario(
        nombre="Existente",
        email="existente@example.com",
        hashed_password=hash_password("password"),
        rol=RolUsuario.INSPECTOR
    )
    db_session.add(user)
    await db_session.commit()
    
    response = await auth_client.post(
        "/equipo/invitar",
        json={"email": "existente@example.com"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Ya existe una cuenta con ese email"


async def test_invitar_inspector_existing_invitation(auth_client: AsyncClient, db_session: AsyncSession, test_user: Usuario):
    # Crear invitación existente
    inv = Invitacion(
        email="pendiente@example.com",
        admin_id=test_user.id,
        token="token_falso",
        estado=EstadoInvitacion.PENDIENTE,
        expira_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(inv)
    await db_session.commit()
    
    response = await auth_client.post(
        "/equipo/invitar",
        json={"email": "pendiente@example.com"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Ya hay una invitación pendiente para ese email"


async def test_ver_equipo(auth_client: AsyncClient, db_session: AsyncSession, test_user: Usuario):
    # Crear un miembro del equipo
    inspector = Usuario(
        nombre="Inspector",
        email="inspector@example.com",
        hashed_password=hash_password("password"),
        rol=RolUsuario.INSPECTOR,
        admin_id=test_user.id
    )
    db_session.add(inspector)
    
    # Crear una invitación pendiente
    inv = Invitacion(
        email="invitado@example.com",
        admin_id=test_user.id,
        token="token_123",
        estado=EstadoInvitacion.PENDIENTE,
        expira_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(inv)
    await db_session.commit()
    
    response = await auth_client.get("/equipo")
    assert response.status_code == 200
    data = response.json()
    
    # Puede que test_user esté en la base de datos o haya más, pero filtramos por miembros del test_user (solo el inspector)
    assert len(data["miembros"]) == 1
    assert data["miembros"][0]["email"] == "inspector@example.com"
    
    assert len(data["invitaciones_pendientes"]) == 1
    assert data["invitaciones_pendientes"][0]["email"] == "invitado@example.com"


async def test_dar_de_baja_inspector(auth_client: AsyncClient, db_session: AsyncSession, test_user: Usuario):
    inspector = Usuario(
        nombre="Baja",
        email="baja@example.com",
        hashed_password=hash_password("password"),
        rol=RolUsuario.INSPECTOR,
        admin_id=test_user.id
    )
    db_session.add(inspector)
    await db_session.commit()
    await db_session.refresh(inspector)
    
    response = await auth_client.delete(f"/equipo/{inspector.id}")
    assert response.status_code == 204
    
    # Verificar que el usuario no está activo
    await db_session.refresh(inspector)
    assert inspector.is_active is False


async def test_dar_de_baja_inspector_not_found(auth_client: AsyncClient):
    response = await auth_client.delete("/equipo/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Inspector no encontrado"


async def test_cancelar_invitacion(auth_client: AsyncClient, db_session: AsyncSession, test_user: Usuario):
    inv = Invitacion(
        email="cancelar@example.com",
        admin_id=test_user.id,
        token="token_cancel",
        estado=EstadoInvitacion.PENDIENTE,
        expira_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    
    response = await auth_client.delete(f"/equipo/invitaciones/{inv.id}")
    assert response.status_code == 204
    
    # Verificar que se borró
    result = await db_session.execute(select(Invitacion).where(Invitacion.id == inv.id))
    assert result.scalar_one_or_none() is None


async def test_cancelar_invitacion_not_found(auth_client: AsyncClient):
    response = await auth_client.delete("/equipo/invitaciones/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Invitación no encontrada"
