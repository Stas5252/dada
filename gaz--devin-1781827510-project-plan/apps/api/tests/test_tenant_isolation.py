import pytest
from uuid import uuid4
from app.context import current_tenant_id
from app.store_factory import get_app_store
from sqlalchemy import text

from app.schemas import AgentCreateRequest

@pytest.fixture
def db_store():
    return get_app_store()

@pytest.mark.asyncio
async def test_tenant_isolation(db_store):
    """
    Доказывает, что RLS работает и Тенант А не может прочитать данные Тенанта Б.
    """
    test_tenant_id = uuid4()
    tenant_b_id = uuid4()
    
    test_tenant_id_str = str(test_tenant_id)
    tenant_b_id_str = str(tenant_b_id)
    
    # Создаем агента для тенанта А (test_tenant_id)
    agent_a_name = "Agent A"
    current_tenant_id.set(test_tenant_id_str)
    agent_a = db_store.create_agent(
        tenant_id=test_tenant_id,
        payload=AgentCreateRequest(name=agent_a_name, prompt="I am Agent A prompt", channel="web"),
    )
    agent_a_id = str(agent_a.id)
    
    # Создаем тенанта Б напрямую через raw sql
    with db_store._session_scope() as session:
        session.execute(
            text("INSERT INTO tenants (id, name, plan, status, settings) VALUES (:id, :name, 'start', 'active', '{}') ON CONFLICT DO NOTHING"),
            {"id": tenant_b_id_str, "name": "Tenant B"}
        )
    
    # Создаем агента Б под тенантом Б
    current_tenant_id.set(tenant_b_id_str)
    agent_b_name = "Agent B"
    agent_b = db_store.create_agent(
        tenant_id=tenant_b_id,
        payload=AgentCreateRequest(name=agent_b_name, prompt="I am Agent B prompt", channel="web"),
    )
    agent_b_id = str(agent_b.id)
    
    # 1. Запрашиваем из контекста тенанта А
    current_tenant_id.set(test_tenant_id_str)
    agents_a_list = db_store.list_agents(test_tenant_id)
    agent_ids_a = {str(a.id) for a in agents_a_list}
    
    assert agent_a_id in agent_ids_a, "Тенант А должен видеть своего агента"
    assert agent_b_id not in agent_ids_a, "Тенант А НЕ должен видеть агента Б"
    
    # 2. Запрашиваем из контекста тенанта Б
    current_tenant_id.set(tenant_b_id_str)
    agents_b_list = db_store.list_agents(tenant_b_id)
    agent_ids_b = {str(a.id) for a in agents_b_list}
    
    assert agent_b_id in agent_ids_b, "Тенант Б должен видеть своего агента"
    assert agent_a_id not in agent_ids_b, "Тенант Б НЕ должен видеть агента А"
    
    # Очистка
    with db_store._session_scope() as session:
        session.execute(text("DELETE FROM agents WHERE id = :id"), {"id": agent_a_id})
        session.execute(text("DELETE FROM agents WHERE id = :id"), {"id": agent_b_id})
        session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_b_id_str})
