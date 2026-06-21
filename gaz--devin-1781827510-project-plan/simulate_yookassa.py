import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = "http://127.0.0.1:8000/api/v1"

async def check_billing_status():
    logger.info("Checking Billing Status...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/billing/status",
            headers={"x-tenant-id": TENANT_ID}
        )
        logger.info(f"Billing Status: {resp.status_code} {resp.text}")

async def simulate_limit_exhaustion():
    pass

async def simulate_yookassa_payment():
    logger.info("Sending YooKassa payment.succeeded event to upgrade tenant to 'pro'...")
    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "22e12f66-000f-5000-8000-18db351245c7",
            "status": "succeeded",
            "amount": {
                "value": "1000.00",
                "currency": "RUB"
            },
            "metadata": {
                "tenant_id": TENANT_ID,
                "plan_name": "pro"
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/billing/yookassa/webhook", json=payload)
        logger.info(f"YooKassa Webhook Response: {resp.status_code} {resp.text}")

async def main():
    await check_billing_status()
    await simulate_yookassa_payment()
    await check_billing_status()

if __name__ == "__main__":
    asyncio.run(main())
