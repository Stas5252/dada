import asyncio
import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import AuthContext, resolve_current_principal
from app.orchestrator import AgentOrchestrator
from app.schemas import TestbedReadinessResponse, TestCase, TestCaseCreate, TestCaseStatus, TestRun
from app.settings import get_settings
from app.store_factory import AppStore, get_app_store
from app.testbed_readiness import build_testbed_readiness

router = APIRouter(tags=["Testbed"])
logger = logging.getLogger(__name__)


@router.post(
    "/agents/{agent_id}/testbed/cases",
    response_model=TestCase,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    agent_id: UUID,
    payload: TestCaseCreate,
    auth_context: AuthContext = Depends(resolve_current_principal),
    store: AppStore = Depends(get_app_store),
) -> TestCase:
    agent = store.get_agent(auth_context.tenant.id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return store.create_test_case(auth_context.tenant.id, agent_id, payload)


@router.get(
    "/agents/{agent_id}/testbed/cases",
    response_model=list[TestCase],
)
def list_test_cases(
    agent_id: UUID,
    auth_context: AuthContext = Depends(resolve_current_principal),
    store: AppStore = Depends(get_app_store),
) -> list[TestCase]:
    agent = store.get_agent(auth_context.tenant.id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return store.list_test_cases(auth_context.tenant.id, agent_id)


@router.get(
    "/agents/{agent_id}/testbed/readiness",
    response_model=TestbedReadinessResponse,
)
def get_testbed_readiness(
    agent_id: UUID,
    auth_context: AuthContext = Depends(resolve_current_principal),
    store: AppStore = Depends(get_app_store),
) -> TestbedReadinessResponse:
    agent = store.get_agent(auth_context.tenant.id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return build_testbed_readiness(
        agent=agent,
        test_cases=store.list_test_cases(auth_context.tenant.id, agent_id),
        test_runs=store.list_test_runs(auth_context.tenant.id, agent_id),
    )


@router.post(
    "/agents/{agent_id}/testbed/cases/{test_case_id}/run",
    response_model=TestRun,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_test_case(
    agent_id: UUID,
    test_case_id: UUID,
    auth_context: AuthContext = Depends(resolve_current_principal),
    store: AppStore = Depends(get_app_store),
) -> TestRun:
    agent = store.get_agent(auth_context.tenant.id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    test_case = store.get_test_case(auth_context.tenant.id, agent_id, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TestCase not found",
        )
    test_run = store.create_test_run(auth_context.tenant.id, agent_id, test_case_id)
    
    settings = get_settings()

    async def execute_test() -> None:
        orchestrator = AgentOrchestrator(store, settings)
        
        user_simulation_prompt = (
            f"You are a user in a simulated test. Follow this scenario: {test_case.scenario}. "
            "End the conversation by explicitly saying '[END]' if your goal is achieved or if you reach a dead end."
        )
        
        from app.llm_router import LLMRouter, RoutingStrategy
        router_llm = LLMRouter(settings)
        
        logs: list[dict[str, object]] = []
        current_user_message = "Здравствуйте!"
        max_turns = 10
        conversation_id = uuid4()
        
        try:
            for _i in range(max_turns):
                logs.append({"role": "customer", "content": current_user_message})
                
                result = await orchestrator.process_message(
                    tenant_id=auth_context.tenant.id,
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    customer_message=current_user_message,
                    channel="testbed"
                )
                agent_response = result.response_text or ""
                logs.append({"role": "agent", "content": agent_response})
                
                user_messages = [{"role": "system", "content": user_simulation_prompt}]
                for log in logs:
                    r = "assistant" if log["role"] == "customer" else "user"
                    user_messages.append({"role": r, "content": str(log["content"])})
                    
                simulated_reply_content, _ = await router_llm.generate_response(
                    system_prompt=user_simulation_prompt,
                    messages=user_messages,
                    strategy=RoutingStrategy.FASTEST
                )
                
                current_user_message = simulated_reply_content
                
                if "[END]" in current_user_message or "goodbye" in current_user_message.lower() or "до свидания" in current_user_message.lower():
                    logs.append({"role": "customer", "content": current_user_message})
                    break
                    
            eval_prompt = f"""
Given the following scenario and expected outcome:
Scenario: {test_case.scenario}
Expected Outcome: {test_case.expected_outcome}

And the following conversation transcript:
{json.dumps(logs, indent=2, ensure_ascii=False)}

Did the agent successfully achieve the expected outcome?
Reply ONLY with "PASSED" or "FAILED" on the first line, followed by a brief summary on the next line.
"""
            eval_result_content, _ = await router_llm.generate_response(
                system_prompt="You are an objective evaluator.",
                messages=[{"role": "user", "content": eval_prompt}],
                strategy=RoutingStrategy.SMARTEST
            )
            
            eval_text = eval_result_content.strip()
            if eval_text.startswith("PASSED"):
                final_status = TestCaseStatus.passed
                summary = eval_text[6:].strip()
            else:
                final_status = TestCaseStatus.failed
                summary = eval_text[6:].strip() if eval_text.startswith("FAILED") else eval_text
                
            store.update_test_run(
                tenant_id=auth_context.tenant.id,
                agent_id=agent_id,
                test_run_id=test_run.id,
                status=final_status,
                logs=logs,
                result_summary=summary
            )
        except Exception as e:
            logger.exception("Test execution failed")
            store.update_test_run(
                tenant_id=auth_context.tenant.id,
                agent_id=agent_id,
                test_run_id=test_run.id,
                status=TestCaseStatus.failed,
                logs=logs,
                result_summary=f"Error: {str(e)}"
            )

    def run_sync() -> None:
        asyncio.run(execute_test())
        
    store.background_jobs.submit(test_run.id, run_sync)
    
    return test_run


@router.get(
    "/agents/{agent_id}/testbed/runs",
    response_model=list[TestRun],
)
def list_test_runs(
    agent_id: UUID,
    test_case_id: UUID | None = None,
    auth_context: AuthContext = Depends(resolve_current_principal),
    store: AppStore = Depends(get_app_store),
) -> list[TestRun]:
    agent = store.get_agent(auth_context.tenant.id, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return store.list_test_runs(auth_context.tenant.id, agent_id, test_case_id)
