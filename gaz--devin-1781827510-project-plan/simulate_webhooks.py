import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default dev DB has:
TENANT_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = "http://127.0.0.1:8000/api/v1/webhooks"

async def set_tenant_settings():
    # To test fully, we'd need to set the tokens in DB via settings API, 
    # but the API doesn't care if token is invalid for receiving messages, 
    # only for sending back it will fail with a 401/400 from Meta/VK.
    # Our goal is to ensure the webhook parses the payload and calls the orchestrator.
    pass

async def test_whatsapp_challenge():
    logger.info("Testing WhatsApp Webhook Verification...")
    async with httpx.AsyncClient() as client:
        # Without setting whatsapp_verify_token in DB, this will fail 403, 
        # but that proves the route works and checks the token.
        resp = await client.get(
            f"{BASE_URL}/whatsapp/{TENANT_ID}",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "1158201444"
            }
        )
        logger.info(f"WhatsApp Verification Status (Expected 403 unless token is set): {resp.status_code}")

async def test_whatsapp_message():
    logger.info("Testing WhatsApp Incoming Message...")
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "12345", "phone_number_id": "12345"},
                            "contacts": [{"profile": {"name": "Test User"}, "wa_id": "15551234567"}],
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.HBgL",
                                    "timestamp": "1603059201",
                                    "text": {"body": "Hello WA Orchestrator!"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/whatsapp/{TENANT_ID}", json=payload)
        logger.info(f"WhatsApp Message Response: {resp.status_code} {resp.text}")


async def test_vk_confirmation():
    logger.info("Testing VK Confirmation Challenge...")
    payload = {
        "type": "confirmation",
        "group_id": 123456
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/vk/{TENANT_ID}", json=payload)
        # Expected to return 'ok' if no code is set, or the code if set.
        logger.info(f"VK Confirmation Response: {resp.status_code} {resp.text}")

async def test_vk_message():
    logger.info("Testing VK Incoming Message...")
    payload = {
        "type": "message_new",
        "object": {
            "message": {
                "id": 123,
                "date": 1603059201,
                "peer_id": 987654321,
                "from_id": 987654321,
                "text": "Hello VK Orchestrator!"
            }
        },
        "group_id": 123456
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/vk/{TENANT_ID}", json=payload)
        logger.info(f"VK Message Response: {resp.status_code} {resp.text}")

async def main():
    await test_whatsapp_challenge()
    await test_whatsapp_message()
    await test_vk_confirmation()
    await test_vk_message()

if __name__ == "__main__":
    asyncio.run(main())
