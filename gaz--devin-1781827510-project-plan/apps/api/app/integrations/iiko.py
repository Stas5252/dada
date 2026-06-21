import httpx
import logging

logger = logging.getLogger(__name__)

class IikoCloudClient:
    """Client for iikoCloud API (apiLogin based)."""
    
    def __init__(self, api_login: str):
        self.api_login = api_login
        self.base_url = "https://api-ru.iiko.services/api/1"
        self._token = None
        
    async def _authenticate(self, client: httpx.AsyncClient):
        """Retrieves and caches the bearer token using apiLogin."""
        if self._token:
            return

        payload = {"apiLogin": self.api_login}
        try:
            resp = await client.post(f"{self.base_url}/access_token", json=payload, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("token")
            logger.info("Successfully authenticated with iikoCloud")
        except Exception as e:
            logger.error(f"Failed to authenticate with iikoCloud: {e}")
            raise

    async def get_menu(self, organization_id: str) -> dict:
        """Fetch nomenclature (menu) from iiko."""
        async with httpx.AsyncClient() as client:
            await self._authenticate(client)
            headers = {"Authorization": f"Bearer {self._token}"}
            payload = {
                "organizationId": organization_id
            }
            try:
                # get nomenclature
                resp = await client.post(
                    f"{self.base_url}/nomenclature",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.error(f"Failed to fetch menu from iiko: {e}")
                return {"error": str(e)}

    async def create_delivery_order(self, organization_id: str, phone: str, order_items: list, terminal_group_id: str) -> dict:
        """
        Creates a delivery order in iiko.
        order_items format: [{"productId": "...", "amount": 1}]
        """
        async with httpx.AsyncClient() as client:
            await self._authenticate(client)
            headers = {"Authorization": f"Bearer {self._token}"}
            
            payload = {
                "organizationId": organization_id,
                "terminalGroupId": terminal_group_id,
                "order": {
                    "phone": phone,
                    "items": [
                        {
                            "productId": item["productId"],
                            "amount": item["amount"],
                            "type": "Product"
                        } for item in order_items
                    ],
                }
            }
            try:
                resp = await client.post(
                    f"{self.base_url}/deliveries/create",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"Created iiko order: {data.get('orderInfo', {}).get('id')}")
                return data
            except Exception as e:
                logger.error(f"Failed to create iiko order: {e}")
                return {"error": str(e)}
