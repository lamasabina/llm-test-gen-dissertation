
Here is a test suite using the `requests` library to test the API endpoints:
```
import pytest
import requests

BASE_URL = "http://localhost:80"

@pytest.fixture(scope="module")
def client():
    return requests.Session()

def test_catalogue_get(client):
    response = client.get(f"{BASE_URL}/catalogue")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]

def test_customer_get(client):
    customer_id = "test-001"
    response = client.get(f"{BASE_URL}/customers/{customer_id}")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert "id" in response.json()

def test_customer_post(client):
    payload = {"id": "test-002", "name": "Test User"}
    response = client.post(f"{BASE_URL}/customers", json=payload)
    assert response.status_code in (201, 400, 409)
    if response.status_code == 201:
        assert "id" in response.json()
```
Note that this test suite uses the `pytest` fixture to create a `requests.Session` object that is reused for all tests. This is more efficient than creating a new `requests.Session` object for each test.