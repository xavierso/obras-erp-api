import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.obra import Obra
from app.models.documento import CategoriaDocumento

@pytest.fixture
async def obras_con_documentos(db_session: AsyncSession, test_user, auth_client: AsyncClient):
    # Crear dos obras
    obra1 = Obra(nombre="Obra 1", codigo="OBR-001", usuario_id=test_user.id)
    obra2 = Obra(nombre="Obra 2", codigo="OBR-002", usuario_id=test_user.id)
    db_session.add_all([obra1, obra2])
    await db_session.commit()
    await db_session.refresh(obra1)
    await db_session.refresh(obra2)

    # Subir documentos a obra1
    await auth_client.post(
        f"/obras/{obra1.id}/documentos",
        data={"categoria": CategoriaDocumento.PLANOS.value},
        files={"archivo": ("plano1.pdf", b"contenido", "application/pdf")}
    )
    # Subir documentos a obra2
    await auth_client.post(
        f"/obras/{obra2.id}/documentos",
        data={"categoria": CategoriaDocumento.FACTURAS.value},
        files={"archivo": ("factura2.pdf", b"contenido", "application/pdf")}
    )
    return [obra1, obra2]

@pytest.mark.asyncio
async def test_listar_todos_los_documentos(auth_client: AsyncClient, obras_con_documentos):
    response = await auth_client.get("/documentos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    nombres_archivos = [d["nombre_original"] for d in data]
    assert "plano1.pdf" in nombres_archivos
    assert "factura2.pdf" in nombres_archivos
    assert "obra_nombre" in data[0]
    assert "obra_codigo" in data[0]

@pytest.mark.asyncio
async def test_listar_todos_los_documentos_filtrado(auth_client: AsyncClient, obras_con_documentos):
    response = await auth_client.get(
        "/documentos",
        params={"categoria": CategoriaDocumento.PLANOS.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nombre_original"] == "plano1.pdf"
