import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.integrations.amocrm import AmoCRMClient
from app.integrations.iiko import IikoCloudClient

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_amocrm_create_lead(mock_post):
    # Mock contact response
    mock_contact_resp = MagicMock()
    mock_contact_resp.json.return_value = {
        "_embedded": {
            "contacts": [{"id": 12345}]
        }
    }
    mock_contact_resp.raise_for_status = lambda: None
    
    # Mock lead response
    mock_lead_resp = MagicMock()
    mock_lead_resp.json.return_value = {
        "_embedded": {
            "leads": [{"id": 67890}]
        }
    }
    mock_lead_resp.raise_for_status = lambda: None
    
    mock_post.side_effect = [mock_contact_resp, mock_lead_resp]
    
    client = AmoCRMClient(domain="test.amocrm.ru", access_token="fake-token")
    result = await client.create_lead(name="Ivan", phone="+79991234567", tags=["AI Order"], pipeline_id=100)
    
    assert result == {"lead_id": 67890, "contact_id": 12345}
    
    # Verify contact payload
    call_1_kwargs = mock_post.call_args_list[0][1]
    assert call_1_kwargs["json"][0]["name"] == "Ivan"
    assert call_1_kwargs["json"][0]["custom_fields_values"][0]["values"][0]["value"] == "+79991234567"
    
    # Verify lead payload
    call_2_kwargs = mock_post.call_args_list[1][1]
    lead_payload = call_2_kwargs["json"][0]
    assert lead_payload["name"] == "Лид от AI: Ivan"
    assert lead_payload["pipeline_id"] == 100
    assert lead_payload["_embedded"]["tags"][0]["name"] == "AI Order"
    assert lead_payload["_embedded"]["contacts"][0]["id"] == 12345


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_iiko_create_order(mock_post):
    # Mock token response
    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = {"token": "fake-iiko-token"}
    mock_token_resp.raise_for_status = lambda: None
    
    # Mock order response
    mock_order_resp = MagicMock()
    mock_order_resp.json.return_value = {
        "orderInfo": {
            "id": "iiko-order-uuid"
        }
    }
    mock_order_resp.raise_for_status = lambda: None
    
    mock_post.side_effect = [mock_token_resp, mock_order_resp]
    
    client = IikoCloudClient(api_login="fake-login")
    result = await client.create_delivery_order(
        organization_id="org-id",
        phone="+79991234567",
        order_items=[{"productId": "prod-1", "amount": 2}],
        terminal_group_id="term-1"
    )
    
    assert result == {"orderInfo": {"id": "iiko-order-uuid"}}
    
    # Verify auth payload
    assert mock_post.call_args_list[0][1]["json"] == {"apiLogin": "fake-login"}
    
    # Verify order payload
    order_payload = mock_post.call_args_list[1][1]["json"]
    assert order_payload["organizationId"] == "org-id"
    assert order_payload["terminalGroupId"] == "term-1"
    assert order_payload["order"]["phone"] == "+79991234567"
    assert order_payload["order"]["items"][0]["productId"] == "prod-1"
    assert order_payload["order"]["items"][0]["amount"] == 2
