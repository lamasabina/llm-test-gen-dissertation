
import pytest
import requests

@pytest.fixture(scope="module")
def client():
    return requests.Session()

class TestAPI:
    def test_catalogue_get(self, client):
        response = client.get("http://localhost:80/catalogue")
        assert response.status_code == 200
        assert "products" in response.json()

    def test_catalogue_get_by_id(self, client):
        response = client.get("http://localhost:80/catalogue/1")
        assert response.status_code == 200
        assert "product" in response.json()

    def test_carts_get(self, client):
        response = client.get("http://localhost:80/carts/1")
        assert response.status_code == 200
        assert "cart" in response.json()

    def test_carts_post(self, client):
        response = client.post("http://localhost:80/carts")
        assert response.status_code == 201
        assert "cart" in response.json()

    def test_carts_items_get(self, client):
        response = client.get("http://localhost:80/carts/1/items")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_carts_items_post(self, client):
        response = client.post("http://localhost:80/carts/1/items")
        assert response.status_code == 201
        assert "item" in response.json()

    def test_orders_get(self, client):
        response = client.get("http://localhost:80/orders")
        assert response.status_code == 200
        assert "orders" in response.json()

    def test_orders_post(self, client):
        response = client.post("http://localhost:80/orders")
        assert response.status_code == 201
        assert "order" in response.json()

    def test_customers_get(self, client):
        response = client.get("http://localhost:80/customers/1")
        assert response.status_code == 200
        assert "customer" in response.json()

    def test_customers_post(self, client):
        response = client.post("http://localhost:80/customers")
        assert response.status_code == 201
        assert "customer" in response.json()

if __name__ == "__main__":
    pytest.main(["-s", __file__])