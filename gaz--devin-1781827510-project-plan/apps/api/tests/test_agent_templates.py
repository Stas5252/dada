"""Test agent templates: presets, API endpoints, tool-registry consistency."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test_run.db")

from app.agent_templates import TEMPLATES, AgentTemplate, get_template, list_templates
from app.schemas import AgentCreateRequest
from app.tool_registry import TOOL_REGISTRY


def test_all_templates_have_required_fields():
    """Every template must have non-empty id, name, description, category, prompt."""
    templates = list_templates()
    assert len(templates) >= 10, f"Expected at least 10 templates, got {len(templates)}"
    for t in templates:
        assert t.id, f"Template missing id"
        assert t.name, f"Template {t.id} missing name"
        assert t.description, f"Template {t.id} missing description"
        assert t.category, f"Template {t.id} missing category"
        assert t.prompt, f"Template {t.id} missing prompt"
        assert len(t.prompt) >= 10, f"Template {t.id} prompt too short"


def test_template_tools_exist_in_registry():
    """All enabled_tools in templates must be registered in TOOL_REGISTRY."""
    for t in list_templates():
        for tool in t.enabled_tools:
            assert tool in TOOL_REGISTRY, (
                f"Template '{t.id}' references tool '{tool}' not in TOOL_REGISTRY"
            )


def test_template_always_includes_escalate_to_human():
    """Every template must include escalate_to_human."""
    for t in list_templates():
        assert "escalate_to_human" in t.enabled_tools, (
            f"Template '{t.id}' missing escalate_to_human"
        )


def test_dental_clinic_has_no_cart_tools():
    """Dental clinic should NOT have order/cart tools."""
    t = get_template("dental_clinic")
    assert t is not None
    cart_tools = {"add_to_cart", "remove_from_cart", "checkout_cart", "confirm_order"}
    actual_tools = set(t.enabled_tools)
    overlap = cart_tools & actual_tools
    assert not overlap, f"Dental clinic should not have cart tools: {overlap}"


def test_restaurant_has_cart_tools():
    """Restaurant template should include order tools."""
    t = get_template("restaurant")
    assert t is not None
    assert "add_to_cart" in t.enabled_tools
    assert "checkout_cart" in t.enabled_tools
    assert "confirm_order" in t.enabled_tools


def test_b2b_has_crm_tools():
    """B2B template should include CRM tools."""
    t = get_template("b2b_sales")
    assert t is not None
    assert "capture_lead" in t.enabled_tools
    assert "create_crm_deal" in t.enabled_tools


def test_template_to_create_payload_is_valid():
    """Each template's payload must be valid for AgentCreateRequest."""
    for t in list_templates():
        payload = t.to_create_payload()
        request = AgentCreateRequest(**payload)
        assert request.name == t.name
        assert request.agent_role == t.agent_role
        assert request.agent_tone == t.agent_tone


def test_get_template_nonexistent_returns_none():
    """get_template for unknown ID returns None."""
    assert get_template("nonexistent_xyz") is None


def test_template_ids_are_unique():
    """All template IDs must be unique."""
    ids = [t.id for t in list_templates()]
    assert len(ids) == len(set(ids)), f"Duplicate template IDs found: {ids}"


def test_template_api_list(client=None):
    """Test GET /agents/templates/list returns all templates."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/api/v1/agents/templates/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 10
        assert all("id" in item for item in data)
        assert all("enabled_tools" in item for item in data)


def test_template_api_get_single():
    """Test GET /agents/templates/{id} returns correct template."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/api/v1/agents/templates/dental_clinic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "dental_clinic"
        assert data["category"] == "healthcare"


def test_template_api_get_nonexistent():
    """Test GET /agents/templates/{id} returns 404 for unknown template."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/api/v1/agents/templates/nonexistent_xyz")
        assert resp.status_code == 404
