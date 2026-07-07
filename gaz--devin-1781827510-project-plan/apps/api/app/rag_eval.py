import re

from app.rag import RetrievalResult, compose_grounded_answer
from app.schemas import (
    KnowledgeSource,
    KnowledgeSourceStatus,
    RagEvalCaseCreate,
    RagEvalCaseResult,
    RagEvalRequest,
    RagEvalResponse,
    RagEvalStatus,
)

TOKEN_PATTERN = re.compile(r"\w+")


def _tokens(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.casefold()))


def _normalized_phrase(value: str) -> str:
    return " ".join(value.casefold().split())


def _source_score(query: str, source: KnowledgeSource) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    source_tokens = _tokens(f"{source.title} {source.content}")
    return len(query_tokens & source_tokens) / len(query_tokens)


def _is_expected_title_match(title: str, expected_titles: list[str]) -> bool:
    normalized_title = _normalized_phrase(title)
    return any(
        expected in normalized_title or normalized_title in expected
        for expected in (_normalized_phrase(candidate) for candidate in expected_titles)
    )


def _rank_sources(query: str, sources: list[KnowledgeSource]) -> list[tuple[float, KnowledgeSource]]:
    ranked = [
        (_source_score(query, source), source)
        for source in sources
        if source.status != KnowledgeSourceStatus.failed and source.content.strip()
    ]
    return sorted(ranked, key=lambda item: (item[0], item[1].updated_at), reverse=True)


def _evaluate_case(
    case: RagEvalCaseCreate,
    sources: list[KnowledgeSource],
    min_relevance_score: float,
) -> RagEvalCaseResult:
    ranked_sources = _rank_sources(case.query, sources)
    relevant_sources = [(score, source) for score, source in ranked_sources if score >= min_relevance_score]
    top_score, top_source = relevant_sources[0] if relevant_sources else (0.0, None)
    retrieved_titles = [source.title for score, source in ranked_sources[:3] if score > 0.0]
    citation_titles = [top_source.title] if top_source else []
    source_content = top_source.content if top_source else ""

    expected_terms = [_normalized_phrase(term) for term in case.expected_answer_terms if term.strip()]
    normalized_content = _normalized_phrase(source_content)
    matched_terms: list[str] = []
    missing_terms: list[str] = []
    for original, normalized in zip(case.expected_answer_terms, expected_terms, strict=False):
        if not normalized:
            continue
        if normalized in normalized_content:
            matched_terms.append(original)
        else:
            missing_terms.append(original)

    failures: list[str] = []
    no_answer_respected = not case.should_answer and top_source is None

    if case.should_answer:
        if top_source is None:
            failures.append("no_relevant_source")
        elif not citation_titles:
            failures.append("missing_citation")
        if case.expected_source_titles and (
            top_source is None or not _is_expected_title_match(top_source.title, case.expected_source_titles)
        ):
            failures.append("expected_source_not_retrieved")
        if missing_terms:
            failures.append("expected_terms_missing")
    else:
        if top_source is not None:
            failures.append("unexpected_answer_source")

    status = RagEvalStatus.passed if not failures else RagEvalStatus.failed
    answer_preview = compose_grounded_answer(case.query, None if top_source is None else _to_retrieval_result(top_source, top_score))

    return RagEvalCaseResult(
        name=case.name,
        status=status,
        query=case.query,
        should_answer=case.should_answer,
        retrieved_source_titles=retrieved_titles,
        citation_titles=citation_titles,
        matched_expected_terms=matched_terms,
        missing_expected_terms=missing_terms,
        no_answer_respected=no_answer_respected,
        relevance_score=round(top_score, 4),
        answer_preview=answer_preview,
        failures=failures,
    )


def _to_retrieval_result(source: KnowledgeSource, score: float) -> RetrievalResult:
    return RetrievalResult(
        source_id=source.id,
        title=source.title,
        excerpt=source.content[:300],
        score=score,
    )


def evaluate_rag_cases(payload: RagEvalRequest, sources: list[KnowledgeSource]) -> RagEvalResponse:
    results = [
        _evaluate_case(case, sources, payload.min_relevance_score)
        for case in payload.cases
    ]
    passed_cases = sum(1 for result in results if result.status == RagEvalStatus.passed)
    total_cases = len(results)
    pass_rate = passed_cases / total_cases if total_cases else 0.0
    status = RagEvalStatus.passed if pass_rate >= payload.required_pass_rate else RagEvalStatus.failed

    return RagEvalResponse(
        status=status,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        pass_rate=pass_rate,
        required_pass_rate=payload.required_pass_rate,
        min_relevance_score=payload.min_relevance_score,
        results=results,
    )
