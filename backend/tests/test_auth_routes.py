"""
Tests para los endpoints de autenticación.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.security import _token_blacklist


@pytest.fixture(autouse=True)
def clear_blacklist():
    """Limpiar blacklist antes de cada test."""
    _token_blacklist.clear()
    yield
    _token_blacklist.clear()


@pytest.fixture
async def client():
    """Cliente HTTP async para tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestLoginJSON:
    """Tests para el endpoint /api/auth/login/json."""

    async def test_login_success(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login/json",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    async def test_login_wrong_password(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login/json",
            json={"username": "admin", "password": "wrong_password"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login/json",
            json={"username": "noexiste", "password": "admin123"},
        )
        assert response.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login/json",
            json={"username": "admin"},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestGetMe:
    """Tests para el endpoint /api/auth/me."""

    async def test_get_me_authenticated(self, client: AsyncClient):
        # Login primero
        login_resp = await client.post(
            "/api/auth/login/json",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_resp.json()["access_token"]

        # Obtener perfil
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token_invalido"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogout:
    """Tests para el endpoint /api/auth/logout."""

    async def test_logout_invalidates_token(self, client: AsyncClient):
        # Login
        login_resp = await client.post(
            "/api/auth/login/json",
            json={"username": "admin", "password": "admin123"},
        )
        token = login_resp.json()["access_token"]

        # Verificar que el token funciona
        me_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200

        # Logout
        logout_resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_resp.status_code == 200

        # El token ya no debe funcionar
        me_resp2 = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp2.status_code == 401


@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Tests para verificar que los endpoints protegidos requieren auth."""

    async def test_ventas_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/ventas")
        assert response.status_code == 401

    async def test_dashboard_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/dashboard/metricas")
        assert response.status_code == 401

    async def test_export_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/export/csv")
        assert response.status_code == 401

    async def test_proveedores_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/proveedores/lista")
        assert response.status_code == 401

    async def test_vendedores_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/vendedores")
        assert response.status_code == 401

    async def test_health_is_public(self, client: AsyncClient):
        """Health check debe ser público."""
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_root_is_public(self, client: AsyncClient):
        """Root endpoint debe ser público."""
        response = await client.get("/")
        assert response.status_code == 200
