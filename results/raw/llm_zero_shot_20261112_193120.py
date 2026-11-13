
```
import pytest
import requests

@pytest.fixture
def client():
    return requests.Session()

def test_get_catalogue(client):
    response = client.get(f"{BASE_URL}/catalogue")
    assert response.status_code == 200
    assert response.json()[0]["id"]

def test_get_product(client):
    response = client.get(f"{BASE_URL}/catalogue/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"]

def test_post_product(client):
    response = client.post(f"{BASE_URL}/catalogue", json={"name": "New Product", "description": "New product description", "price": 10.99})
    assert response.status_code == 201
    assert response.json()["id"]

def test_put_product(client):
    response = client.put(f"{BASE_URL}/catalogue/{product_id}", json={"name": "Updated Product", "description": "Updated product description", "price": 11.99})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Product"

def test_delete_product(client):
    response = client.delete(f"{BASE_URL}/catalogue/{product_id}")
    assert response.status_code == 204

def test_get_order(client):
    response = client.get(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["id"]

def test_post_order(client):
    response = client.post(f"{BASE_URL}/orders", json={"customerId": "1234", "products": [{"id": "123", "quantity": 2}]})
    assert response.status_code == 201
    assert response.json()["id"]

def test_put_order(client):
    response = client.put(f"{BASE_URL}/orders/{order_id}", json={"customerId": "1234", "products": [{"id": "123", "quantity": 2}]})
    assert response.status_code == 200
    assert response.json()["id"]

def test_delete_order(client):
    response = client.delete(f"{BASE_URL}/orders/{order_id}")
    assert response.status_code == 204

def test_get_customer(client):
    response = client.get(f"{BASE_URL}/customers/{customer_id}")
    assert response.status_code == 200
    assert response.json()["id"]

def test_post_customer(client):
    response = client.post(f"{BASE_URL}/customers", json={"name": "New Customer", "email": "new@customer.com"})
    assert response.status_code == 201
    assert response.json()["id"]

def test_put_customer(client):
    response = client.put(f"{BASE_URL}/customers/{customer_id}", json={"name": "Updated Customer", "email": "updated@customer.com"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Customer"

def test_delete_customer(client):
    response = client.delete(f"{BASE_URL}/customers/{customer_id}")
    assert response.status_code == 204
```

This test suite uses the `requests` library to make HTTP requests to the REST API and assert the HTTP status codes and JSON response bodies. It also includes tests for the `catalogue`, `orders`, `customers`, and `products` endpoints.

Note that the `client` fixture is used to create a new `requests.Session` object for each test, which is then used to make the HTTP requests. This allows the tests to be run in parallel, as each test has its own `requests.Session` object.