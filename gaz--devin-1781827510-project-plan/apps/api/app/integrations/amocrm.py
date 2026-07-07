import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

class AmoCRMClient:
    """Client for AmoCRM integration using Bearer Token (Long-Lived or OAuth)."""
    
    def __init__(self, domain: str, access_token: str) -> None:
        self.domain = domain.rstrip('/')
        self.access_token = access_token
        self.base_url = f"https://{self.domain}/api/v4"
    
    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_lead(
        self,
        name: str,
        phone: str | None = None,
        tags: list[str] | None = None,
        pipeline_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Creates a Lead and a Contact in AmoCRM, links them together.
        Returns the created lead info.
        """
        from app.security import SSRFTransport
        async with httpx.AsyncClient(transport=SSRFTransport()) as client:
            # 1. Create a contact if phone is provided
            contact_id = None
            if phone:
                contact_payload = {
                    "name": name,
                    "custom_fields_values": [
                        {
                            "field_code": "PHONE",
                            "values": [
                                {
                                    "value": phone,
                                    "enum_code": "WORK"
                                }
                            ]
                        }
                    ]
                }
                
                try:
                    resp = await client.post(
                        f"{self.base_url}/contacts",
                        json=[contact_payload],
                        headers=self._headers,
                        timeout=10.0
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    contact_id = data["_embedded"]["contacts"][0]["id"]
                    logger.info(f"Created AmoCRM Contact: {contact_id}")
                except Exception as e:
                    logger.error(f"Failed to create AmoCRM contact: {e}")
                    # Continue without contact_id if it fails
            
            # 2. Create the lead
            lead_payload: dict[str, Any] = {
                "name": f"Лид от AI: {name}",
                "price": 0
            }
            if pipeline_id:
                lead_payload["pipeline_id"] = pipeline_id
                
            if tags:
                lead_payload["_embedded"] = {
                    "tags": [{"name": tag} for tag in tags]
                }
                
            if contact_id:
                if "_embedded" not in lead_payload:
                    lead_payload["_embedded"] = {}
                lead_payload["_embedded"]["contacts"] = [{"id": contact_id}]

            try:
                resp = await client.post(
                    f"{self.base_url}/leads",
                    json=[lead_payload],
                    headers=self._headers,
                    timeout=10.0
                )
                resp.raise_for_status()
                data = resp.json()
                lead_id = data["_embedded"]["leads"][0]["id"]
                logger.info(f"Created AmoCRM Lead: {lead_id}")
                return {"lead_id": lead_id, "contact_id": contact_id}
            except Exception as e:
                logger.error(f"Failed to create AmoCRM lead: {e}")
                return {"error": str(e)}
