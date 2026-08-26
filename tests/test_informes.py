import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.obra import Obra
from app.models.visita import Visita

@pytest.fixture
async def setup_obra_visita(db_session: AsyncSession, test_user):
    obra = Obra(
        codigo="OBRA-INF",
        nombre="Obra Informe Test",
        usuario_id=test_user.id
    )
    db_session.add(obra)
    await db_session.commit()
    await db_session.refresh(obra)

    visita = Visita(
        obra_id=obra.id,
        usuario_id=test_user.id,
        descripcion="Visita test informe"
    )
    db_session.add(visita)
    await db_session.commit()
    await db_session.refresh(visita)

    return obra, visita

@pytest.mark.asyncio
async def test_generar_informe_completo(auth_client: AsyncClient, setup_obra_visita):
    obra, visita = setup_obra_visita
    
    with patch("app.routers.informes.generar_informe_pdf", return_value=b"fake_pdf_content"):
        response = await auth_client.get(f"/obras/{obra.id}/informe")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"] == f'attachment; filename="informe_{obra.codigo}.pdf"'
        assert response.content == b"fake_pdf_content"

@pytest.mark.asyncio
async def test_generar_informe_visita_especifica(auth_client: AsyncClient, setup_obra_visita):
    obra, visita = setup_obra_visita
    
    with patch("app.routers.informes.generar_informe_pdf", return_value=b"fake_pdf_content"):
        response = await auth_client.get(f"/obras/{obra.id}/informe?visita_id={visita.id}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"] == f'attachment; filename="informe_{obra.codigo}_visita_{visita.id}.pdf"'
        assert response.content == b"fake_pdf_content"

@pytest.mark.asyncio
async def test_generar_informe_obra_no_encontrada(auth_client: AsyncClient):
    response = await auth_client.get("/obras/999/informe")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Obra no encontrada"

@pytest.mark.asyncio
async def test_generar_informe_visita_no_encontrada(auth_client: AsyncClient, setup_obra_visita):
    obra, visita = setup_obra_visita
    
    response = await auth_client.get(f"/obras/{obra.id}/informe?visita_id=999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Visita no encontrada en esta obra"

@pytest.mark.asyncio
async def test_generar_informe_no_autorizado(async_client: AsyncClient, setup_obra_visita):
    obra, visita = setup_obra_visita
    response = await async_client.get(f"/obras/{obra.id}/informe")
    
    assert response.status_code == 401
