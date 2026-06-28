import logging
import re
from collections.abc import Mapping
from typing import Any, cast

logger = logging.getLogger(__name__)

Node = dict[str, Any]
Edge = dict[str, Any]


def clean_label(label: str) -> str:
    if not label:
        return ""
    label = re.sub(
        r"^(интент|ключ|переход|intent|key|trigger)\s*:\s*",
        "",
        label,
        flags=re.IGNORECASE,
    )
    return label.strip().lower()


def match_intent(customer_text: str, edge_label: str) -> bool:
    cleaned_text = customer_text.strip().lower()
    cleaned_label = clean_label(edge_label)
    if not cleaned_label:
        return False
    if cleaned_label in cleaned_text or cleaned_text in cleaned_label:
        return True
    words = re.split(r"[\s,;|]+", cleaned_label)
    return bool(words) and any(w and w in cleaned_text for w in words if len(w) > 2)


def _json_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, Any], item) for item in value if isinstance(item, dict)]


def _node_label(node: Mapping[str, Any]) -> str:
    data = node.get("data")
    if not isinstance(data, Mapping):
        return ""
    return str(data.get("label", ""))


def _find_node(nodes: list[Node], node_id: object) -> Node | None:
    return next((node for node in nodes if str(node.get("id")) == str(node_id)), None)


def _is_start_node(node: Mapping[str, Any]) -> bool:
    label = _node_label(node).lower()
    return node.get("type") == "input" or str(node.get("id")) == "1" or "начало" in label or "start" in label


def interpret_pathway(agent: Any, previous_messages: list[Any], customer_text: str) -> str | None:
    nodes = _json_dicts(getattr(agent, "pathway_nodes", None))
    edges = _json_dicts(getattr(agent, "pathway_edges", None))

    if not nodes or not edges:
        return None

    logger.info("Interpreting visual pathway for agent %s with %s nodes", getattr(agent, "id", "unknown"), len(nodes))

    agent_messages = [message for message in previous_messages if getattr(message, "role", "") == "agent"]

    if not agent_messages:
        start_node = next((node for node in nodes if _is_start_node(node)), None) or nodes[0]
        next_edge = next((edge for edge in edges if str(edge.get("source")) == str(start_node.get("id"))), None)
        if next_edge:
            welcome_node = _find_node(nodes, next_edge.get("target"))
            if welcome_node:
                return _node_label(welcome_node) or None
        return _node_label(start_node) or None

    last_agent_text = str(getattr(agent_messages[-1], "content", ""))

    current_node: Node | None = None
    for node in nodes:
        label = _node_label(node)
        if label and (label in last_agent_text or last_agent_text in label):
            current_node = node
            break

    if not current_node:
        for node in nodes:
            label = _node_label(node)
            if not label:
                continue
            words_label = set(re.findall(r"\w+", label.lower()))
            words_agent = set(re.findall(r"\w+", last_agent_text.lower()))
            if len(words_label.intersection(words_agent)) >= 2:
                current_node = node
                break

    if not current_node:
        return None

    outgoing_edges = [edge for edge in edges if str(edge.get("source")) == str(current_node.get("id"))]
    if not outgoing_edges:
        return None

    next_node: Node | None = None
    fallback_edge: Edge | None = None

    for edge in outgoing_edges:
        edge_label = str(edge.get("label", ""))
        if not edge_label:
            fallback_edge = edge
            continue
        if any(word in edge_label.lower() for word in ["fallback", "default", "иначе"]):
            fallback_edge = edge
            continue
        if match_intent(customer_text, edge_label):
            next_node = _find_node(nodes, edge.get("target"))
            break

    if not next_node and fallback_edge:
        next_node = _find_node(nodes, fallback_edge.get("target"))

    if not next_node and outgoing_edges:
        next_node = _find_node(nodes, outgoing_edges[0].get("target"))

    if not next_node:
        return None

    next_label = _node_label(next_node)

    if "tool" in next_label.lower() or "create_delivery_order" in next_label or "заказ" in next_label.lower():
        return f"Запрос {next_label} обработан. Заказ успешно оформлен в iikoCloud!"
    if "rag" in next_label.lower() or "knowledge" in next_label.lower():
        return None

    return next_label or None
