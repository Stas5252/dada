from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.rag_eval import evaluate_rag_cases
from app.schemas import KnowledgeSource, RagEvalRequest


def test_rag_eval_checks_citations_terms_and_no_answer_policy() -> None:
    tenant_id = uuid4()
    source = KnowledgeSource(
        tenant_id=tenant_id,
        title="Delivery FAQ",
        source_type="manual",
        content="Delivery takes 45 minutes. Free delivery starts from 1000 RUB.",
    )
    payload = RagEvalRequest(
        cases=[
            {
                "name": "Delivery answer",
                "query": "How many minutes does delivery take?",
                "expected_source_titles": ["Delivery FAQ"],
                "expected_answer_terms": ["45 minutes", "Free delivery"],
            },
            {
                "name": "Unknown repair request",
                "query": "Do you repair laptops?",
                "should_answer": False,
            },
        ]
    )

    result = evaluate_rag_cases(payload, [source])

    assert result.status == "passed"
    assert result.pass_rate == 1
    assert result.results[0].citation_titles == ["Delivery FAQ"]
    assert result.results[0].matched_expected_terms == ["45 minutes", "Free delivery"]
    assert result.results[1].no_answer_respected is True
    assert result.results[1].citation_titles == []


def test_rag_eval_api_is_tenant_scoped() -> None:
    client = TestClient(create_app())
    first_email = f"rag_eval_{uuid4().hex}@example.com"
    second_email = f"rag_eval_other_{uuid4().hex}@example.com"

    first_register = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "RAG Eval Co",
            "owner_email": first_email,
            "owner_name": "Owner",
            "password": "safe-local-password",
        },
    )
    assert first_register.status_code == 201
    first_payload = first_register.json()
    first_headers = {
        "Authorization": f"Bearer {first_payload['access_token']}",
        "x-tenant-id": first_payload["tenant"]["id"],
    }

    second_register = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Other RAG Co",
            "owner_email": second_email,
            "owner_name": "Owner",
            "password": "safe-local-password",
        },
    )
    assert second_register.status_code == 201
    second_payload = second_register.json()
    second_headers = {
        "Authorization": f"Bearer {second_payload['access_token']}",
        "x-tenant-id": second_payload["tenant"]["id"],
    }

    source_response = client.post(
        "/api/v1/knowledge/sources",
        headers=first_headers,
        json={
            "title": "Pizza Delivery FAQ",
            "source_type": "manual",
            "content": "Pizza delivery takes 45 minutes inside the city.",
        },
    )
    assert source_response.status_code == 201

    eval_payload = {
        "cases": [
            {
                "name": "Delivery tenant check",
                "query": "pizza delivery minutes",
                "expected_source_titles": ["Pizza Delivery FAQ"],
                "expected_answer_terms": ["45 minutes"],
            }
        ]
    }

    first_eval = client.post("/api/v1/knowledge/eval", headers=first_headers, json=eval_payload)
    assert first_eval.status_code == 200
    assert first_eval.json()["status"] == "passed"

    second_eval = client.post("/api/v1/knowledge/eval", headers=second_headers, json=eval_payload)
    assert second_eval.status_code == 200
    assert second_eval.json()["status"] == "failed"
    assert second_eval.json()["results"][0]["failures"] == [
        "no_relevant_source",
        "expected_source_not_retrieved",
        "expected_terms_missing",
    ]
