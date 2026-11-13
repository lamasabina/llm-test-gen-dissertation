```
import pytest
import requests

BASE_URL = 'http://localhost:80'

@pytest.mark.parametrize('endpoint', ['/catalogue', '/catalogue/{id}', '/carts/{id}', '/carts', '/carts/{id}/items', '/orders', '/orders', '/customers/{id}', '/customers'])
def test_endpoints(endpoint):
    response = requests.get(BASE_URL + endpoint)
    assert response.status_code == 200
    if response.json():
        assert response.json()['data']
```
This test suite uses the `pytest.mark.parametrize` decorator to parameterize the test function with all the endpoints defined in the OpenAPI specification. The `requests` library is used to make GET requests to the endpoints and assert the HTTP status code is 200. If the response contains JSON data, the test asserts that the JSON data contains at least one field.