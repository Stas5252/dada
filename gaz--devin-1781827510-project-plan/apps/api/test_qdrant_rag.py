import asyncio
import logging

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_url_ingestion():
    logger.info("Logging in...")
    async with httpx.AsyncClient() as client:
        # Login
        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "owner@demo-pizza.example.com", "password": "safe-local-password"}
        )
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        logger.info("Uploading URL to knowledge base...")
        # Create URL source
        url_resp = await client.post(
            f"{BASE_URL}/knowledge/upload-url",
            json={"url": "https://python.org"},
            headers=headers
        )
        url_resp.raise_for_status()
        source = url_resp.json()
        logger.info(f"Created knowledge source: {source['title']}")
        
        # Trigger ingestion
        ingest_resp = await client.post(
            f"{BASE_URL}/knowledge/sources/{source['id']}/ingest",
            headers=headers
        )
        ingest_resp.raise_for_status()
        logger.info(f"Triggered ingestion job: {ingest_resp.json()['id']}")
        
        # Wait for ingestion to complete
        await asyncio.sleep(2)
        
        # Get agent list
        agents_resp = await client.get(
            f"{BASE_URL}/agents",
            headers=headers
        )
        agents_resp.raise_for_status()
        agents = agents_resp.json()
        agent_id = agents[0]["id"]
        
        # We can't directly search through API yet unless we use the Mock Chat endpoint.
        # Let's test the mock chat which uses the RAG layer.
        logger.info("Testing RAG retrieval via mock chat...")
        chat_resp = await client.post(
            f"{BASE_URL}/chat/mock",
            json={
                "agent_id": agent_id,
                "message": "Что написано на главной странице python.org?",
                "channel": "web_widget"
            },
            headers=headers
        )
        if chat_resp.status_code == 200:
            data = chat_resp.json()
            agent_msg = data["agent_message"]["content"]
            sources = [s["title"] for s in data.get("sources", [])]
            logger.info(f"Agent response: {agent_msg}")
            logger.info(f"Sources used: {sources}")
        else:
            logger.error(f"Chat error: {chat_resp.text}")

async def main():
    await test_url_ingestion()

if __name__ == "__main__":
    asyncio.run(main())
