import asyncio
import logging
from app.api.v1.crm import get_db_session_factory
from app.database import session_scope
from app.db_models import TenantModel
from app.llm import get_llm_router
from app.settings import get_settings
from app.store_factory import get_app_store
from app.weekly_report import generate_weekly_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cron_weekly_report")

async def run_weekly_reports() -> None:
    logger.info("Starting weekly report generation for all active tenants...")
    settings = get_settings()
    app_store = get_app_store(settings=settings)
    llm_router = get_llm_router(settings)
    factory = get_db_session_factory()
    
    tenant_ids = []
    with session_scope(factory) as session:
        tenants = session.query(TenantModel).filter(TenantModel.status == "active").all()
        for t in tenants:
            tenant_ids.append(t.id)
            
    logger.info(f"Found {len(tenant_ids)} active tenants.")
    
    for tid in tenant_ids:
        try:
            logger.info(f"Generating report for tenant {tid}")
            from uuid import UUID
            await generate_weekly_report(UUID(tid), app_store, llm_router)
        except Exception as e:
            logger.error(f"Error generating report for tenant {tid}: {e}")
            
    logger.info("Weekly report generation finished.")

if __name__ == "__main__":
    asyncio.run(run_weekly_reports())
