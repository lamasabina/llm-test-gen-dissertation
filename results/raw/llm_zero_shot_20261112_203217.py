```
import pytest
import requests

BASE_URL = "http://localhost:80"

@pytest.mark.parametrize("endpoint", ["/catalogue", "/catalogue/{id}", "/carts/{id}", "/carts", "/carts/{id}/items", "/orders", "/orders/{id}", "/customers/{id}", "/customers"])
def test_endpoints(endpoint):
    response = requests.get(BASE_URL + endpoint)
    assert response.status_code == 200
    if response.json():
        assert response.json()["data"]
```
This test suite uses the `pytest.mark.parametrize` fixture to iterate over all endpoints defined in the OpenAPI specification. For each endpoint, it sends a GET request to the corresponding URL and asserts that the response has a status code of 200. Additionally, if the response has a JSON body, it asserts that the JSON body contains at least one field.