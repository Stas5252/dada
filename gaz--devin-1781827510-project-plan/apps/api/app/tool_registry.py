from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

JsonSchema = dict[str, Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    category: str
    description: str
    parameters: JsonSchema
    prompt_rules: tuple[str, ...] = ()

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": deepcopy(self.parameters),
            },
        }


DEFAULT_ENABLED_TOOLS: tuple[str, ...] = ("escalate_to_human",)

ORDER_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "add_to_cart",
        "remove_from_cart",
        "checkout_cart",
        "confirm_order",
    }
)

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "escalate_to_human": ToolDefinition(
        name="escalate_to_human",
        category="handoff",
        description=(
            "Transfer the conversation to a human operator when the request needs a person, "
            "the customer is angry, or the assistant cannot answer safely."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        prompt_rules=(
            "Use escalate_to_human immediately when the customer asks for a person, is angry, "
            "or the request is outside the enabled knowledge/tools.",
        ),
    ),
    "add_to_cart": ToolDefinition(
        name="add_to_cart",
        category="orders",
        description="Add a product or service item to the current order draft.",
        parameters={
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product or service name"},
                "quantity": {"type": "integer", "description": "Quantity", "default": 1},
                "price": {"type": "integer", "description": "Unit price in the account currency", "default": 0},
                "product_external_id": {
                    "type": "string",
                    "description": "External product ID from the knowledge base or catalog",
                },
            },
            "required": ["product_name"],
        },
        prompt_rules=("Use add_to_cart only when the customer clearly wants to buy or order an item.",),
    ),
    "remove_from_cart": ToolDefinition(
        name="remove_from_cart",
        category="orders",
        description="Remove a product or service item from the current order draft.",
        parameters={
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product or service name"},
            },
            "required": ["product_name"],
        },
        prompt_rules=("Use remove_from_cart only when the customer asks to remove an item from the order.",),
    ),
    "checkout_cart": ToolDefinition(
        name="checkout_cart",
        category="orders",
        description="Save customer contact details needed to finalize the current order draft.",
        parameters={
            "type": "object",
            "properties": {
                "customer_phone": {"type": "string", "description": "Customer phone number"},
                "delivery_address": {"type": "string", "description": "Delivery or service address"},
            },
            "required": ["customer_phone", "delivery_address"],
        },
        prompt_rules=(
            "Before checkout_cart, ask for and confirm the customer's phone and delivery/service address.",
        ),
    ),
    "confirm_order": ToolDefinition(
        name="confirm_order",
        category="orders",
        description="Finalize the current order draft and send it to the connected order integration.",
        parameters={"type": "object", "properties": {}, "required": []},
        prompt_rules=(
            "Use confirm_order only after the customer explicitly confirms the order contents and total.",
        ),
    ),
}

REGISTERED_TOOL_NAMES: frozenset[str] = frozenset(TOOL_REGISTRY)


def normalize_enabled_tools(enabled_tools: Sequence[str] | None) -> list[str]:
    requested_tools = list(enabled_tools or DEFAULT_ENABLED_TOOLS)
    normalized: list[str] = []
    for tool_name in requested_tools:
        if tool_name in TOOL_REGISTRY and tool_name not in normalized:
            normalized.append(tool_name)
    if "escalate_to_human" not in normalized:
        normalized.insert(0, "escalate_to_human")
    return normalized


def build_openai_tools(enabled_tools: Sequence[str] | None) -> list[dict[str, Any]]:
    return [
        TOOL_REGISTRY[tool_name].as_openai_tool()
        for tool_name in normalize_enabled_tools(enabled_tools)
        if tool_name in TOOL_REGISTRY
    ]


def build_tool_prompt_rules(enabled_tools: Sequence[str] | None) -> list[str]:
    rules: list[str] = []
    for tool_name in normalize_enabled_tools(enabled_tools):
        tool_definition = TOOL_REGISTRY.get(tool_name)
        if tool_definition is None:
            continue
        rules.extend(tool_definition.prompt_rules)
    return rules


def enabled_tools_include_orders(enabled_tools: Sequence[str] | None) -> bool:
    return bool(ORDER_TOOL_NAMES.intersection(normalize_enabled_tools(enabled_tools)))
