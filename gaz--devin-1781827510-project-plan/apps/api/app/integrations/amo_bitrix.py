import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


async def trigger_crm_webhook(tenant_id: str, lead_data: dict[str, Any], webhook_url: str) -> bool:
    """
    Generic webhook trigger for external CRMs (Bitrix24 / AmoCRM).
    In a real scenario, this would use the specific CRM format or call amocrm.py.
    """
    logger.info(f"Triggering CRM webhook for tenant {tenant_id} to {webhook_url}")
    
    from app.security import SSRFTransport
    try:
        async with httpx.AsyncClient(transport=SSRFTransport(), timeout=5.0) as client:
            resp = await client.post(webhook_url, json=lead_data)
            if resp.status_code in (200, 201, 202, 204):
                logger.info(f"CRM webhook succeeded: {resp.status_code}")
                return True
            else:
                logger.warning(f"CRM webhook failed with status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"CRM webhook exception: {e}")
        return False
