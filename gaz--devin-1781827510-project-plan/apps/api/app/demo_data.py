from uuid import NAMESPACE_URL, UUID, uuid5

from app.rbac import Role
from app.schemas import (
    Agent,
    AgentStatus,
    ChatMessageRequest,
    KnowledgeSource,
    KnowledgeSourceStatus,
    Tenant,
    User,
)

DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
# Local demo fixture only; never used as a production secret.
DEMO_OWNER_PASSWORD = "safe-local-password"  # nosec B105
DEMO_OWNER_EMAIL = "owner@demo-pizza.example.com"


def demo_uuid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"gaz-demo:{name}")


def build_demo_tenant(tenant_id: UUID = DEMO_TENANT_ID) -> Tenant:
    return Tenant(id=tenant_id, name="Demo Pizza", plan="pilot")


def build_demo_owner(tenant_id: UUID = DEMO_TENANT_ID) -> User:
    return User(
        id=demo_uuid("user:owner"),
        tenant_id=tenant_id,
        email=DEMO_OWNER_EMAIL,
        name="Demo Owner",
        role=Role.owner,
    )


def build_demo_agents(tenant_id: UUID = DEMO_TENANT_ID) -> list[Agent]:
    return [
        Agent(
            id=demo_uuid("agent:restaurant-support"),
            tenant_id=tenant_id,
            name="Restaurant Support RU",
            prompt=(
                "Ты AI-оператор ресторана Demo Pizza. Отвечай коротко, используй "
                "только подтвержденные источники, при сомнении передавай оператору."
            ),
            status=AgentStatus.published,
            channel="telegram",
            version=1,
        ),
        Agent(
            id=demo_uuid("agent:web-widget"),
            tenant_id=tenant_id,
            name="Website Widget Concierge",
            prompt=(
                "Помогай гостям сайта с меню, доставкой, оплатой и передачей "
                "сложных вопросов оператору."
            ),
            status=AgentStatus.draft,
            channel="web_widget",
            version=1,
        ),
    ]


def build_demo_knowledge_sources(tenant_id: UUID = DEMO_TENANT_ID) -> list[KnowledgeSource]:
    return [
        KnowledgeSource(
            id=demo_uuid("knowledge:delivery-faq"),
            tenant_id=tenant_id,
            title="Demo Pizza: доставка и оплата",
            source_type="manual",
            content=(
                "Доставка Demo Pizza занимает 45-60 минут. Бесплатная доставка "
                "доступна при заказе от 1000 рублей. Оплата доступна картой, "
                "наличными курьеру или по ссылке YooKassa. Заказы можно изменить "
                "только до передачи на кухню."
            ),
            status=KnowledgeSourceStatus.pending,
            chunk_count=0,
        ),
        KnowledgeSource(
            id=demo_uuid("knowledge:menu-faq"),
            tenant_id=tenant_id,
            title="Demo Pizza: меню и FAQ",
            source_type="manual",
            content=(
                "В меню есть пепперони 30 см за 690 рублей, маргарита 30 см за "
                "590 рублей и вегетарианская пицца 30 см за 650 рублей. Острая "
                "пепперони содержит томаты, моцареллу и пепперони. Пиццы без "
                "глютена пока нет, такой запрос нужно передать оператору."
            ),
            status=KnowledgeSourceStatus.pending,
            chunk_count=0,
        ),
    ]


def build_demo_chat_requests(agent_id: UUID) -> list[ChatMessageRequest]:
    return [
        ChatMessageRequest(
            agent_id=agent_id,
            channel="telegram",
            message="Сколько занимает доставка и от какой суммы она бесплатная?",
        ),
        ChatMessageRequest(
            agent_id=agent_id,
            channel="web_widget",
            message="Есть ли пицца без глютена?",
        ),
        ChatMessageRequest(
            agent_id=agent_id,
            channel="web_widget",
            message="Можно ли оформить корпоративный кейтеринг на 200 человек?",
        ),
    ]
