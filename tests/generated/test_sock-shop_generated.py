```
import pytest
import requests


@pytest.mark.parametrize("url", ["http://localhost:8080/health"])
def test_health(url):
    """Test the /health endpoint"""
    response = requests.get(url)
    assert response.status_code == 200


@pytest.mark.parametrize("url", ["http://localhost:8080/catalogue"])
def test_catalogue(url):
    """Test the /catalogue endpoint"""
    response = requests.get(url)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.parametrize("url", ["http://localhost:8080/carts"])
def test_carts_post(url):
    """Test the /carts POST endpoint"""
    response = requests.post(url, json={"items": [{"itemId": "123", "quantity": 1}]})
    assert response.status_code == 201


@pytest.mark.parametrize("url", ["http://localhost:8080/carts/{cart_id}"])
def test_carts_get(url):
    """Test the /carts GET endpoint"""
    response = requests.get(url)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.parametrize("url", ["http://localhost:8080/carts/{cart_id}"])
def test_carts_delete(url):
    """Test the /carts DELETE endpoint"""
    response = requests.delete(url)
    assert response.status_code == 204


@pytest.mark.parametrize("url", ["http://localhost:8080/carts/{cart_id}/items/{item_id}"])
def test_carts_items_get(url):
    """Test the /carts/items GET endpoint"""
    response = requests.get(url)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.parametrize("url", ["http://localhost:8080/carts/{cart_id}/items/{item_id}"])
def test_carts_items_put(url):
    """Test the /carts/items PUT endpoint"""
    response = requests.put(url, json={"quantity": 2})
    assert response.status_code == 200


@pytest.mark.parametrize("url", ["http://localhost:8080/carts/{cart_id}/items/{item_id}"])
def test_carts_items_delete(url):
    """Test the /carts/items DELETE endpoint"""
    response = requests.delete(url)
    assert response.status_code == 204
```