from uuid import uuid4

from app.orchestrator import AgentOrchestrator
from app.schemas import Agent, AgentCreateRequest
from app.settings import Settings
from app.store import InMemoryStore


def test_agent_create_request_normalizes_profile_lists() -> None:
    payload = AgentCreateRequest(
        name="Profile Agent",
        prompt="Answer from approved knowledge and escalate unknown requests.",
        forbidden_topics="legal advice\nmedical guarantees, unapproved discounts",
        enabled_tools=["confirm_order", "missing_tool", "confirm_order"],
    )

    assert payload.forbidden_topics == [
        "legal advice",
        "medical guarantees",
        "unapproved discounts",
    ]
    assert payload.enabled_tools == ["escalate_to_human", "confirm_order"]


def test_system_prompt_uses_agent_profile_without_order_context() -> None:
    store = InMemoryStore()
    orchestrator = AgentOrchestrator(store, Settings(llm_provider="mock"))
    agent = Agent(
        tenant_id=uuid4(),
        name="Clinic Reception",
        prompt="Book appointments only from confirmed clinic data.",
        business_profile="Private clinic in Samara with pediatrics and diagnostics.",
        agent_role="receptionist",
        agent_tone="professional",
        agent_language="ru",
        business_hours="Mon-Fri 09:00-18:00",
        escalation_rules="Escalate emergency symptoms and payment disputes.",
        forbidden_topics=["diagnosis promises"],
        enabled_tools=["escalate_to_human"],
    )

    prompt = orchestrator._build_system_prompt(
        agent=agent,
        channel="web_widget",
        retrieval_results=[],
    )

    assert "Primary role: receptionist." in prompt
    assert "Tone: professional." in prompt
    assert "Private clinic in Samara" in prompt
    assert "Escalate emergency symptoms" in prompt
    assert "- diagnosis promises" in prompt
    assert "CURRENT CART" not in prompt
    assert "add_to_cart" not in prompt


def test_system_prompt_adds_order_rules_only_when_order_tools_enabled() -> None:
    store = InMemoryStore()
    orchestrator = AgentOrchestrator(store, Settings(llm_provider="mock"))
    agent = Agent(
        tenant_id=uuid4(),
        name="Restaurant Support",
        prompt="Use confirmed menu data only.",
        business_profile="Restaurant delivery assistant.",
        enabled_tools=[
            "escalate_to_human",
            "add_to_cart",
            "checkout_cart",
            "confirm_order",
        ],
    )

    prompt = orchestrator._build_system_prompt(
        agent=agent,
        channel="telegram",
        retrieval_results=[],
    )

    assert "Use add_to_cart only" in prompt
    assert "Before checkout_cart" in prompt
    assert "Use confirm_order only" in prompt
    assert "CURRENT CART: Empty" in prompt
