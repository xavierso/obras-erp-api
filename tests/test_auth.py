import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usuario import Usuario

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, test_user: Usuario):
    response = await async_client.post(
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "password"  # Asumiendo que esta es la contraseña cruda
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_fail(async_client: AsyncClient, test_user: Usuario):
    response = await async_client.post(
        "/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me(auth_client: AsyncClient, test_user: Usuario):
    response = await auth_client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["nombre"] == test_user.nombre
