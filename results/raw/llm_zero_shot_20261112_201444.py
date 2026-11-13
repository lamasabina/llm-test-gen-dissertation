
Here is a sample Python pytest test suite using the `requests` library to test the REST API described in the OpenAPI specification:
```
import pytest
import requests

BASE_URL = 'http://localhost:80'

@pytest.mark.parametrize('endpoint', ['/catalogue', '/catalogue/{id}', '/carts/{id}', '/carts', '/carts/{id}/items', '/orders', '/orders/{id}', '/customers/{id}', '/customers'])
def test_endpoints(endpoint):
    response = requests.get(BASE_URL + endpoint)
    assert response.status_code == 200
    assert response.json()
```
This test suite uses the `pytest.mark.parametrize` decorator to parameterize the test function with all the endpoints defined in the OpenAPI specification. The test function then sends a GET request to the endpoint using the `requests` library and asserts that the response has a status code of 200 and that the response body is a JSON object.

Note that this is just a sample test suite and you may need to modify it to fit your specific requirements. Additionally, you may want to add more tests to cover other aspects of the API, such as error handling, authentication, and input validation.