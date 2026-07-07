import json
import logging
from uuid import UUID

from app.llm import LLMRouter, get_llm_router
from app.schemas import QAEvaluation
from app.store_factory import AppStore

logger = logging.getLogger(__name__)


async def evaluate_conversation(tenant_id: UUID, conversation_id: UUID, app_store: AppStore, llm_router: LLMRouter) -> None:
    """Evaluate a conversation and store the QA result."""
    conversation = app_store.get_conversation(tenant_id, conversation_id)
    if not conversation:
        logger.error(f"QA: Conversation {conversation_id} not found")
        return

    messages = app_store.list_messages(tenant_id, conversation_id)
    if not messages:
        return

    chat_history = []
    for msg in messages:
        chat_history.append(f"{msg.role.value}: {msg.content}")

    chat_text = "\n".join(chat_history)

    prompt = f"""
    Оцени качество работы AI-агента в следующем диалоге.
    Верни ответ в формате JSON:
    {{
      "score": int (от 0 до 10, где 10 - идеально),
      "flags": list[str] (список проблем, например "грубость", "неверная информация", "уход от темы", если есть),
      "feedback": str (краткий комментарий по работе агента)
    }}

    Диалог:
    {chat_text}
    """

    try:
        content, _ = await llm_router.generate_response(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(content)
        evaluation = QAEvaluation(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            score=int(result.get("score", 0)),
            flags=result.get("flags", []),
            feedback=result.get("feedback", "")
        )
        app_store.save_qa_evaluation(evaluation)
        logger.info(f"QA Evaluation saved for {conversation_id}: score {evaluation.score}")
    except Exception as e:
        logger.error(f"Failed to evaluate conversation {conversation_id}: {e}")
