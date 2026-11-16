import pytest

pytestmark = pytest.mark.api


def test_home_responds_success_when_api_is_up(client):
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "API funcionando correctamente"}
