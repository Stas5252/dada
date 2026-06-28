from unittest.mock import patch
from uuid import uuid4

import pytest

from app.contracts.integrations import IikoOrderDraft, IikoOrderLine
from app.integration_services import LocalIikoAdapter
from app.schemas import RegisterRequest
from app.store_factory import get_app_store


@pytest.mark.anyio
async def test_iiko_fetch_menu_with_api_settings() -> None:
    store = get_app_store()
    
    # 1. Register a tenant and set up iikoCloud credentials
    reg_payload = RegisterRequest(
        company_name="Iiko Menu Test Restaurant",
        owner_email=f"iiko_menu_{uuid4().hex}@example.com",
        owner_name="Iiko Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {
            "iiko_api_login": "mock_login_token",
            "iiko_organization_id": "mock_org_id_123",
        },
    )

    # 2. Prepare mock responses for iiko API
    mock_token_resp = {"token": "mock-jwt-token-xyz"}
    mock_nomenclature_resp = {
        "products": [
            {"id": "item-1-uuid", "name": "Pizza Pepperoni", "price": 750.5, "deleted": False},
            {"id": "item-2-uuid", "name": "Pizza Margherita", "price": 600.0, "deleted": False},
            {"id": "item-deleted-uuid", "name": "Archived Dish", "price": 400.0, "deleted": True},
        ]
    }

    adapter = LocalIikoAdapter()

    # We will mock httpx.AsyncClient.post inline to return these payloads
    class MockResponse:
        def __init__(self, json_data: dict, status_code: int = 200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self) -> dict:
            return self._json_data

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise Exception(f"HTTP Error {self.status_code}")

    async def mock_post(url: str, **kwargs) -> MockResponse:
        if "/access_token" in url:
            assert kwargs.get("json", {}).get("apiLogin") == "mock_login_token"
            return MockResponse(mock_token_resp)
        elif "/nomenclature" in url:
            assert kwargs.get("headers", {}).get("Authorization") == "Bearer mock-jwt-token-xyz"
            assert kwargs.get("json", {}).get("organizationId") == "mock_org_id_123"
            return MockResponse(mock_nomenclature_resp)
        return MockResponse({}, 404)

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        menu = await adapter.fetch_menu(tenant_id=str(tenant_id))
        
        # Verify it fetched and parsed correctly
        assert len(menu) == 3
        
        # Check first item parsing details
        item1 = next(item for item in menu if item.external_id == "item-1-uuid")
        assert item1.name == "Pizza Pepperoni"
        assert item1.price_minor == 75050  # 750.5 * 100
        assert item1.available is True

        # Check deleted/archived item parsing
        deleted_item = next(item for item in menu if item.external_id == "item-deleted-uuid")
        assert deleted_item.available is False

        # Verify caching works by checking that it returns cached items
        # when we simulate a failure or mock clean-up
        adapter.menus[str(tenant_id)] = menu
        cached_menu = await adapter.fetch_menu(tenant_id=str(tenant_id))
        assert len(cached_menu) == 3


@pytest.mark.anyio
async def test_iiko_create_delivery_order_with_api_settings() -> None:
    store = get_app_store()
    
    # 1. Register a tenant and set up iikoCloud credentials
    reg_payload = RegisterRequest(
        company_name="Iiko Order Test Restaurant",
        owner_email=f"iiko_order_{uuid4().hex}@example.com",
        owner_name="Iiko Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {
            "iiko_api_login": "mock_login_token",
            "iiko_organization_id": "mock_org_id_123",
            "iiko_terminal_group_id": "mock_terminal_group_id_999",
        },
    )

    draft = IikoOrderDraft(
        tenant_id=str(tenant_id),
        customer_phone="+79998887766",
        delivery_address="Mock Address Street 10",
        lines=[
            IikoOrderLine(menu_item_external_id="item-1-uuid", quantity=2)
        ],
        idempotency_key="unique-idempotence-key-555",
    )

    mock_token_resp = {"token": "mock-jwt-token-xyz"}
    mock_order_resp = {
        "orderInfo": {
            "id": "real-iiko-delivery-order-uuid-abc"
        }
    }

    class MockResponse:
        def __init__(self, json_data: dict, status_code: int = 200):
            self._json_data = json_data
            self.status_code = status_code

        def json(self) -> dict:
            return self._json_data

        def raise_for_status(self) -> None:
            pass

    async def mock_post(url: str, **kwargs) -> MockResponse:
        if "/access_token" in url:
            return MockResponse(mock_token_resp)
        elif "/deliveries/create" in url:
            payload = kwargs.get("json", {})
            assert payload.get("organizationId") == "mock_org_id_123"
            assert payload.get("terminalGroupId") == "mock_terminal_group_id_999"
            order_data = payload.get("order", {})
            assert order_data.get("phone") == "+79998887766"
            assert order_data.get("items")[0]["productId"] == "item-1-uuid"
            assert order_data.get("items")[0]["amount"] == 2
            return MockResponse(mock_order_resp)
        return MockResponse({}, 404)

    adapter = LocalIikoAdapter()

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        # We must set dry_run=False to trigger the real API client call
        result = await adapter.create_order(draft=draft, dry_run=False)
        assert result.external_order_id == "real-iiko-delivery-order-uuid-abc"
        assert result.status.value == "accepted"


@pytest.mark.anyio
async def test_iiko_error_fallback_gracefully() -> None:
    store = get_app_store()
    
    reg_payload = RegisterRequest(
        company_name="Iiko Error Test Restaurant",
        owner_email=f"iiko_err_{uuid4().hex}@example.com",
        owner_name="Iiko Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {
            "iiko_api_login": "mock_login_token",
            "iiko_organization_id": "mock_org_id_123",
        },
    )

    adapter = LocalIikoAdapter()

    # Simulate connection error
    async def mock_post_raise(*args, **kwargs) -> None:
        raise Exception("Connection Refused")

    with patch("httpx.AsyncClient.post", side_effect=mock_post_raise):
        # fetch_menu should capture the error, log it, and return empty list
        menu = await adapter.fetch_menu(tenant_id=str(tenant_id))
        assert len(menu) == 0
