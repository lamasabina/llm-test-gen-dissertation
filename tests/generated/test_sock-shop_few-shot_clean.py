import requests
import pytest

BASE_URL = "http://localhost:8080"

@pytest.mark.parametrize("endpoint", ["/health", "/catalogue"])
def test_get_endpoints(endpoint):
    response = requests.get(BASE_URL + endpoint)
    assert response.status_code == 200

@pytest.mark.parametrize("endpoint", ["/carts"])
def test_post_endpoint(endpoint):
    response = requests.post(BASE_URL + endpoint, json={"items": [{"itemId": "123", "quantity": 1}]})
    assert response.status_code == 201