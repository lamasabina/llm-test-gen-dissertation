```
import pytest
import requests

BASE_URL = "http://localhost:80"

@pytest.mark.parametrize("endpoint", ["/catalogue", "/catalogue/{id}", "/carts/{id}", "/carts", "/carts/{id}/items", "/orders", "/orders/{id}", "/customers/{id}", "/customers"])
def test_endpoints(endpoint):
    response = requests.get(BASE_URL + endpoint)
    assert response.status_code == 200
    if response.json():
        assert "data" in response.json()
```
This test suite uses the `pytest.mark.parametrize` decorator to generate a test for each endpoint in the OpenAPI specification. The `requests` library is used to make GET requests to each endpoint, and the `assert` statement is used to check the HTTP status code and the presence of a "data" field in the JSON response body. The `pytest.mark.parametrize` decorator takes a list of endpoint URLs as an argument, and each endpoint URL is used to generate a test function. The test function takes a single argument, `endpoint`, which is used to construct the URL for the GET request.