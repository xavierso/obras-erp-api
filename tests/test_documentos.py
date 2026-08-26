import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.obra import Obra
from app.models.documento import CategoriaDocumento

@pytest.fixture
async def test_obra(db_session: AsyncSession, test_user):
    obra = Obra(
        nombre="Obra Test",
        codigo="OBR-001",
        usuario_id=test_user.id
    )
    db_session.add(obra)
    await db_session.commit()
    await db_session.refresh(obra)
    return obra

@pytest.mark.asyncio
async def test_subir_documento(auth_client: AsyncClient, test_obra: Obra):
    response = await auth_client.post(
        f"/obras/{test_obra.id}/documentos",
        data={"categoria": CategoriaDocumento.PLANOS.value},
        files={"archivo": ("plano.pdf", b"contenido pdf", "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["obra_id"] == test_obra.id
    assert data["categoria"] == CategoriaDocumento.PLANOS.value
    assert data["nombre_original"] == "plano.pdf"
    assert "url" in data

@pytest.mark.asyncio
async def test_listar_documentos(auth_client: AsyncClient, test_obra: Obra):
    # Subir un par de documentos primero
    await auth_client.post(
        f"/obras/{test_obra.id}/documentos",
        data={"categoria": CategoriaDocumento.PLANOS.value},
        files={"archivo": ("plano1.pdf", b"contenido pdf 1", "application/pdf")}
    )
    await auth_client.post(
        f"/obras/{test_obra.id}/documentos",
        data={"categoria": CategoriaDocumento.FACTURAS.value},
        files={"archivo": ("factura1.pdf", b"contenido pdf 2", "application/pdf")}
    )

    # Listar todos
    response = await auth_client.get(f"/obras/{test_obra.id}/documentos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Filtrar por categoria
    response_filtrado = await auth_client.get(
        f"/obras/{test_obra.id}/documentos",
        params={"categoria": CategoriaDocumento.PLANOS.value}
    )
    assert response_filtrado.status_code == 200
    data_filtrado = response_filtrado.json()
    assert len(data_filtrado) == 1
    assert data_filtrado[0]["categoria"] == CategoriaDocumento.PLANOS.value

@pytest.mark.asyncio
async def test_subir_documento_obra_inexistente(auth_client: AsyncClient):
    response = await auth_client.post(
        "/obras/999/documentos",
        data={"categoria": CategoriaDocumento.PLANOS.value},
        files={"archivo": ("plano.pdf", b"contenido pdf", "application/pdf")}
    )
    assert response.status_code == 404
