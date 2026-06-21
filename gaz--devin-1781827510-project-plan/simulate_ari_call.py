import asyncio
import logging
import sys
import os

# Ensure the app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "apps", "api")))

from app.asterisk_ari_service import get_asterisk_ari_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def simulate_call():
    logger.info("Starting Asterisk ARI Simulation...")
    ari_service = get_asterisk_ari_service()
    
    # 00000000-0000-0000-0000-000000000001 is the default demo tenant
    # 00000000-0000-0000-0000-000000000010 is the demo agent
    tenant_id = "00000000-0000-0000-0000-000000000001"
    agent_id = "00000000-0000-0000-0000-000000000010"
    channel_id = "SIP/mock-12345"
    caller_number = "+1234567890"

    logger.info(f"Triggering mock StasisStart for channel {channel_id}...")
    await ari_service._handle_stasis_start(
        channel_id=channel_id,
        caller_number=caller_number,
        tenant_id=tenant_id,
        agent_id=agent_id
    )
    logger.info("Simulation completed successfully.")

if __name__ == "__main__":
    asyncio.run(simulate_call())
