```
import pytest
import requests


@pytest.fixture(scope="module")
def client():
    return requests.Session()


@pytest.mark.parametrize("path", ["/catalogue"])
def test_get_catalogue(client, path):
    response = client.get(f"{BASE_URL}{path}")
    assert response.status_code == 200
    assert response.json()["products"][0]["id"]
```