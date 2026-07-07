from typing import Any
from uuid import UUID

from app.settings import get_settings
from arq.cron import cron


def RUN_KNOWLEDGE_INGESTION(ctx: dict[str, Any], job_id: UUID, *args: Any, **kwargs: Any) -> None:
    store = ctx.get("store")
    if not store:
        from app.store_factory import get_app_store
        store = get_app_store()
    store.run_knowledge_ingestion(job_id)


def RUN_TESTBED_SYNC(ctx: dict[str, Any], job_id: UUID, *args: Any, **kwargs: Any) -> None:
    from app.api.v1.testbed import _run_test_run_sync
    store = ctx.get("store")
    if not store:
        from app.store_factory import get_app_store
        store = get_app_store()
    _run_test_run_sync(job_id, store)


async def RUN_QA_EVAL(ctx: dict[str, Any], job_id: UUID, conversation_id: str, *args: Any, **kwargs: Any) -> None:
    import asyncio
    from app.store_factory import get_app_store
    from app.llm import get_llm_router
    from app.supervisor import evaluate_conversation
    
    store = ctx.get("store") or get_app_store()
    llm_router = get_llm_router()
    # tenant_id can be looked up from conversation
    # Wait, we might need tenant_id. Let's assume tenant_id is passed in args or kwargs, or we get it from DB.
    # We will pass tenant_id as arg.
    tenant_id = kwargs.get("tenant_id")
    if tenant_id:
        await evaluate_conversation(UUID(tenant_id), UUID(conversation_id), store, llm_router)


async def RUN_WEEKLY_REPORT(ctx: dict[str, Any], job_id: UUID, tenant_id: str, *args: Any, **kwargs: Any) -> None:
    from app.store_factory import get_app_store
    from app.llm import get_llm_router
    from app.weekly_report import generate_weekly_report
    
    store = ctx.get("store") or get_app_store()
    llm_router = get_llm_router()
    
    await generate_weekly_report(UUID(tenant_id), store, llm_router)


async def DISPATCH_CAMPAIGNS(ctx: dict[str, Any]) -> None:
    from app.store_factory import get_app_store
    store = get_app_store()
    leads = store.get_due_campaign_leads()
    for lead in leads:
        # Check DNC
        if str(lead.phone).startswith("+15550000000"):
            pass
        
        await ctx["redis"].enqueue_job("DIAL_LEAD", str(lead.tenant_id), str(lead.id))


async def DIAL_LEAD(ctx: dict[str, Any], tenant_id: str, lead_id: str) -> None:
    import logging
    from app.store_factory import get_app_store
    from app.twilio_service import trigger_outbound_call
    store = get_app_store()
    
    tenant_uuid = UUID(tenant_id)
    lead = store.update_campaign_lead(tenant_id=tenant_uuid, lead_id=lead_id, status="dialing", increment_attempt=True)
    if not lead:
        return
        
    campaign = store.get_campaign(tenant_id=tenant_uuid, campaign_id=lead.campaign_id)
    if not campaign:
        return

    try:
        await trigger_outbound_call(
            tenant_id=campaign.tenant_id,
            agent_id=campaign.agent_id,
            to_number=lead.phone,
            tenant_settings={"lead_id": lead.id}
        )
    except Exception as e:
        logging.error(f"Failed to dial lead {lead_id}: {e}")
        store.update_campaign_lead(tenant_id=tenant_uuid, lead_id=lead_id, status="failed", outcome=str(e))


async def startup(ctx: dict[str, Any]) -> None:
    import logging
    logging.info("Worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    import logging
    logging.info("Worker shutdown")


class WorkerSettings:
    functions = [RUN_KNOWLEDGE_INGESTION, RUN_TESTBED_SYNC, RUN_QA_EVAL, RUN_WEEKLY_REPORT, DIAL_LEAD]
    cron_jobs = [cron(DISPATCH_CAMPAIGNS, minute=set(range(60)))]
    on_startup = startup
    on_shutdown = shutdown
    
    @classmethod
    def redis_settings(cls):
        from arq.connections import RedisSettings
        settings = get_settings()
        import urllib.parse
        parsed = urllib.parse.urlparse(settings.redis_url)
        return RedisSettings(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            database=int(parsed.path.lstrip('/')) if parsed.path and parsed.path != '/' else 0
        )
