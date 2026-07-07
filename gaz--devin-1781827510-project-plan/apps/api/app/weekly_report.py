import json
import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.llm import LLMRouter, get_llm_router
from app.schemas import WeeklyReport
from app.store_factory import AppStore

logger = logging.getLogger(__name__)


async def generate_weekly_report(tenant_id: UUID, app_store: AppStore, llm_router: LLMRouter) -> None:
    """Generate a weekly analytics AI report for a tenant."""
    now = datetime.now(UTC)
    start_date = now - timedelta(days=7)

    conversations = app_store.list_conversations(tenant_id)
    recent_convs = [c for c in conversations if c.created_at >= start_date]

    if not recent_convs:
        logger.info(f"No conversations in the last 7 days for tenant {tenant_id}")
        return

    # Basic stats
    total = len(recent_convs)
    resolved = sum(1 for c in recent_convs if c.status.value == "resolved")
    automation_rate = (resolved / total * 100) if total > 0 else 0.0

    channel_counts: Counter[str] = Counter()
    for c in recent_convs:
        channel_counts[c.channel] += 1
    
    top_channels = [ch for ch, count in channel_counts.most_common(3)]

    # Gather a sample of conversations (up to 20) for LLM analysis
    sample_convs = recent_convs[:20]
    sample_texts = []
    for c in sample_convs:
        msgs = app_store.list_messages(tenant_id, c.id)
        chat_str = "\n".join([f"{m.role.value}: {m.content}" for m in msgs])
        sample_texts.append(f"Conversation {c.id} (Status: {c.status.value}):\n{chat_str}\n")

    combined_samples = "\n---\n".join(sample_texts)

    prompt = f"""
    Проанализируй сводку диалогов за последнюю неделю для этого аккаунта.
    Всего обращений: {total}
    Автоматизировано: {automation_rate:.1f}%
    Основные каналы: {", ".join(top_channels)}

    Примеры диалогов:
    {combined_samples}

    Напиши короткий аналитический отчет (Weekly AI Report) в формате JSON:
    {{
      "summary": str (общее резюме недели, 2-3 предложения),
      "insights": str (что сработало хорошо, где мы теряем клиентов/деньги, что нужно улучшить в знаниях агента)
    }}
    """

    try:
        content, _ = await llm_router.generate_response(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(content)
        report = WeeklyReport(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=now,
            summary=result.get("summary", ""),
            insights=result.get("insights", ""),
            top_channels=top_channels
        )
        app_store.save_weekly_report(report)
        logger.info(f"Weekly report generated for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to generate weekly report for tenant {tenant_id}: {e}")
