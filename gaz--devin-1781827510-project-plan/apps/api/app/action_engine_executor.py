from typing import Any
from uuid import UUID

from app.contracts.action_engine import (
    ToolContract,
    ToolInvocation,
    ToolPermission,
    assert_tool_invocation_allowed,
    build_tool_audit_event,
)
from app.contracts.integrations import IikoOrderDraft, IikoOrderLine
from app.contracts.types import JsonValue
from app.service_factory import get_iiko_adapter
from app.settings import get_settings
from app.store_factory import AppStore


def _payload_str(payload: dict[str, JsonValue], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _payload_optional_str(payload: dict[str, JsonValue], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _payload_int(payload: dict[str, JsonValue], key: str, default: int = 0) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class ActionEngineExecutor:
    def __init__(self) -> None:
        self.contracts: dict[str, ToolContract] = {
            "escalate_to_human": ToolContract(
                name="escalate_to_human",
                version="1.0",
                input_schema={},
                output_schema={},
                permissions=frozenset({ToolPermission.READ_MENU}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "add_to_cart": ToolContract(
                name="add_to_cart",
                version="1.0",
                input_schema={
                    "product_name": "string",
                    "quantity": "integer",
                    "price": "integer",
                    "product_external_id": "string",
                },
                output_schema={},
                permissions=frozenset({ToolPermission.CREATE_ORDER}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "remove_from_cart": ToolContract(
                name="remove_from_cart",
                version="1.0",
                input_schema={"product_name": "string"},
                output_schema={},
                permissions=frozenset({ToolPermission.CREATE_ORDER}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "checkout_cart": ToolContract(
                name="checkout_cart",
                version="1.0",
                input_schema={"customer_phone": "string", "delivery_address": "string"},
                output_schema={},
                permissions=frozenset({ToolPermission.CREATE_ORDER}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "confirm_order": ToolContract(
                name="confirm_order",
                version="1.0",
                input_schema={},
                output_schema={},
                permissions=frozenset({ToolPermission.CREATE_ORDER}),
                timeout_ms=10_000,
                destructive=True,
                requires_confirmation=True,
            ),
            "capture_lead": ToolContract(
                name="capture_lead",
                version="1.0",
                input_schema={
                    "name": "string",
                    "phone": "string",
                    "email": "string",
                    "source": "string",
                    "notes": "string",
                },
                output_schema={},
                permissions=frozenset({ToolPermission.MANAGE_CRM}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "create_crm_deal": ToolContract(
                name="create_crm_deal",
                version="1.0",
                input_schema={
                    "title": "string",
                    "amount": "integer",
                    "currency": "string",
                },
                output_schema={},
                permissions=frozenset({ToolPermission.MANAGE_CRM}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "book_appointment": ToolContract(
                name="book_appointment",
                version="1.0",
                input_schema={
                    "service": "string",
                    "date": "string",
                    "time": "string",
                    "customer_name": "string",
                    "customer_phone": "string",
                    "notes": "string",
                },
                output_schema={},
                permissions=frozenset({ToolPermission.MANAGE_APPOINTMENTS}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
            "create_task": ToolContract(
                name="create_task",
                version="1.0",
                input_schema={
                    "title": "string",
                    "due_date": "string",
                    "notes": "string",
                },
                output_schema={},
                permissions=frozenset({ToolPermission.MANAGE_CRM}),
                timeout_ms=5_000,
                destructive=False,
                requires_confirmation=False,
            ),
        }

    async def execute_tool(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        invocation: ToolInvocation,
        store: AppStore,
    ) -> dict[str, Any]:
        contract = self.contracts.get(invocation.tool_name)
        if not contract:
            raise ValueError(f"Tool {invocation.tool_name} not registered in Action Engine")

        assert_tool_invocation_allowed(contract, invocation)

        if contract.audit_enabled:
            audit_event = build_tool_audit_event(contract, invocation)
            store.create_audit_log(
                event_type=f"tool_executed:{invocation.tool_name}",
                tenant_id=tenant_id,
                details={
                    "tool_name": audit_event.tool_name,
                    "idempotency_key": audit_event.idempotency_key or "none",
                    "permissions": ",".join(audit_event.permissions),
                },
            )

        tool_name = invocation.tool_name
        payload = invocation.input_payload

        if tool_name == "escalate_to_human":
            store.escalate_conversation(tenant_id, conversation_id)
            return {
                "success": True,
                "message": "Перевожу вас на старшего специалиста. Пожалуйста, подождите.",
                "action_performed": "escalate",
            }

        if tool_name == "add_to_cart":
            product_name = _payload_str(payload, "product_name", "Неизвестно")
            quantity = _payload_int(payload, "quantity", 1)
            price = _payload_int(payload, "price", 0)
            product_external_id = _payload_optional_str(payload, "product_external_id")
            store.add_order_item(
                tenant_id,
                conversation_id,
                product_name,
                quantity,
                price,
                product_external_id,
            )
            return {
                "success": True,
                "message": f"Успешно добавлено в корзину: {product_name} x {quantity}",
                "action_performed": "add_item",
            }

        if tool_name == "remove_from_cart":
            product_name = _payload_str(payload, "product_name")
            store.remove_order_item(tenant_id, conversation_id, product_name)
            return {
                "success": True,
                "message": f"Успешно удалено из корзины: {product_name}",
                "action_performed": "remove_item",
            }

        if tool_name == "checkout_cart":
            customer_phone = _payload_str(payload, "customer_phone")
            delivery_address = _payload_str(payload, "delivery_address")
            store.update_order_draft_checkout_info(
                tenant_id,
                conversation_id,
                customer_phone,
                delivery_address,
            )
            return {
                "success": True,
                "message": (
                    "Контакты сохранены. Попросите клиента окончательно подтвердить "
                    "заказ: состав и сумму."
                ),
                "action_performed": "checkout",
            }

        if tool_name == "confirm_order":
            draft = store.get_order_draft(tenant_id, conversation_id)
            if not draft or not draft.customer_phone or not draft.delivery_address:
                return {
                    "success": False,
                    "message": "Ошибка: нет телефона или адреса. Нужен шаг checkout_cart перед подтверждением.",
                    "action_performed": "confirm_error",
                }

            store.confirm_order_draft(tenant_id, conversation_id)

            iiko = get_iiko_adapter()
            iiko_draft = IikoOrderDraft(
                tenant_id=str(tenant_id),
                customer_phone=draft.customer_phone,
                delivery_address=draft.delivery_address,
                idempotency_key=str(conversation_id),
                lines=[
                    IikoOrderLine(
                        menu_item_external_id=item.product_external_id or "unknown",
                        quantity=item.quantity,
                    )
                    for item in draft.items
                ],
            )
            env_dry = not bool(get_settings().iiko_api_login)
            await iiko.create_order(draft=iiko_draft, dry_run=env_dry)

            return {
                "success": True,
                "message": "Заказ успешно отправлен в ресторан!",
                "action_performed": "confirm",
            }

        if tool_name == "capture_lead":
            name = _payload_str(payload, "name", "Неизвестно")
            phone = _payload_optional_str(payload, "phone")
            email = _payload_optional_str(payload, "email")
            source = _payload_str(payload, "source", "action_engine")
            
            from app.api.v1.crm import auto_create_lead
            lead = auto_create_lead(tenant_id, name, phone, email, source)
            
            if lead:
                from app.integrations.amo_bitrix import trigger_crm_webhook
                import asyncio
                # URL is hardcoded here for testing, normally it should be from tenant_settings
                webhook_url = get_settings().crm_webhook_url or "https://webhook.site/stub"
                lead_data = {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "email": lead.email,
                    "source": lead.source
                }
                try:
                    asyncio.create_task(trigger_crm_webhook(str(tenant_id), lead_data, webhook_url))
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).error("Failed to schedule CRM webhook", exc_info=exc)
                
                return {
                    "success": True,
                    "message": "Контактные данные сохранены в CRM.",
                    "action_performed": "capture_lead",
                }
            return {
                "success": False,
                "message": "Не удалось создать лид, не хватает данных.",
            }

        if tool_name == "create_crm_deal":
            title = _payload_str(payload, "title", "Новая сделка")
            amount_minor = _payload_int(payload, "amount", 0)
            
            from app.db_models import CrmDealModel
            from uuid import uuid4
            
            with app_store._session_scope() as session:
                deal = CrmDealModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    title=title,
                    amount_minor=amount_minor,
                    source="action_engine",
                )
                session.add(deal)
            
            return {
                "success": True,
                "message": f"Сделка '{title}' успешно создана.",
                "action_performed": "create_deal",
            }

        if tool_name == "book_appointment":
            service = _payload_str(payload, "service", "Неизвестная услуга")
            date = _payload_str(payload, "date")
            time = _payload_str(payload, "time")
            customer_name = _payload_str(payload, "customer_name", "Клиент")
            customer_phone = _payload_str(payload, "customer_phone", "")
            
            from app.api.v1.crm import auto_create_lead
            from app.db_models import CrmTaskModel
            from uuid import uuid4
            
            lead = auto_create_lead(tenant_id, customer_name, customer_phone, None, "appointment", app_store)
            lead_id = lead.id if lead else None
            
            with app_store._session_scope() as session:
                task = CrmTaskModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    lead_id=lead_id,
                    title=f"Запись: {service} на {date} в {time}",
                )
                session.add(task)
                
            return {
                "success": True,
                "message": f"Запись на {service} оформлена на {date} {time}.",
                "action_performed": "book_appointment",
            }
            
        if tool_name == "create_task":
            title = _payload_str(payload, "title")
            from app.db_models import CrmTaskModel
            from uuid import uuid4
            
            with app_store._session_scope() as session:
                task = CrmTaskModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    title=title,
                )
                session.add(task)
            
            return {
                "success": True,
                "message": f"Задача '{title}' создана.",
                "action_performed": "create_task",
            }

        return {"success": False, "message": "Unknown tool invocation logic"}
