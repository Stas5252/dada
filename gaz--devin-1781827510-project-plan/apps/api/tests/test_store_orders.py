from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_models import Base
from app.settings import Settings
from app.sqlalchemy_store import SqlAlchemyStore


@pytest.fixture
def store_and_ids() -> tuple[SqlAlchemyStore, UUID, UUID]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    settings = Settings(database_url="sqlite:///:memory:")
    store = SqlAlchemyStore(session_factory, settings)
    
    # Create tenant for foreign keys
    tenant_id = uuid4()
    with store._session_scope() as session:
        from app.db_models import TenantModel
        session.add(TenantModel(id=str(tenant_id), name="Test", status="active", plan="free", settings={}))
        session.commit()
    
    # Create conversation
    conversation_id = uuid4()
    with store._session_scope() as session:
        from app.db_models import AgentModel, ConversationModel
        agent_id = uuid4()
        session.add(AgentModel(id=str(agent_id), tenant_id=str(tenant_id), name="Test", prompt="", status="active", channel="web", version=1, voice_id="", voice_language=""))
        session.add(ConversationModel(id=str(conversation_id), tenant_id=str(tenant_id), agent_id=str(agent_id), channel="web", status="active", summary="", resolution_status="open"))
        session.commit()
    
    return store, tenant_id, conversation_id


def test_add_remove_confirm_order_items(store_and_ids: tuple[SqlAlchemyStore, UUID, UUID]) -> None:
    store, tenant_id, conversation_id = store_and_ids
    
    # Assert get on empty
    draft = store.get_order_draft(tenant_id, conversation_id)
    assert draft is None
    
    # Add item
    draft = store.add_order_item(tenant_id, conversation_id, "Pizza", 2, 500)
    assert draft is not None
    assert draft.status == "draft"
    assert len(draft.items) == 1
    assert draft.items[0].product_name == "Pizza"
    assert draft.items[0].quantity == 2
    assert draft.total_amount == 1000
    
    # Add same item again
    draft = store.add_order_item(tenant_id, conversation_id, "Pizza", 1, 500)
    assert len(draft.items) == 1
    assert draft.items[0].quantity == 3
    assert draft.total_amount == 1500
    
    # Add different item
    draft = store.add_order_item(tenant_id, conversation_id, "Cola", 1, 150)
    assert len(draft.items) == 2
    assert draft.total_amount == 1650
    
    # Remove item
    draft = store.remove_order_item(tenant_id, conversation_id, "Pizza")
    assert draft is not None
    assert len(draft.items) == 1
    assert draft.items[0].product_name == "Cola"
    assert draft.total_amount == 150
    
    # Checkout info
    draft = store.update_order_draft_checkout_info(tenant_id, conversation_id, "+79991234567", "Test Address 123")
    assert draft is not None
    assert draft.customer_phone == "+79991234567"
    assert draft.delivery_address == "Test Address 123"
    
    # Confirm
    draft = store.confirm_order_draft(tenant_id, conversation_id)
    assert draft is not None
    assert draft.status == "confirmed"
