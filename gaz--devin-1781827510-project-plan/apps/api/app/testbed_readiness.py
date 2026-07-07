from datetime import UTC, datetime
from uuid import UUID

from app.publish_gate import evaluate_testbed_publish_gate
from app.schemas import (
    Agent,
    TestbedCaseReadiness,
    TestbedLatestRunSummary,
    TestbedReadinessResponse,
    TestCase,
    TestCaseStatus,
    TestRun,
)

REQUIRED_PASS_RATE = 1.0
MINIMUM_TEST_CASES = 1


def _latest_run_by_case(test_runs: list[TestRun]) -> dict[UUID, TestRun]:
    latest: dict[UUID, TestRun] = {}
    for run in sorted(
        test_runs,
        key=lambda candidate: (candidate.updated_at, candidate.created_at),
        reverse=True,
    ):
        latest.setdefault(run.test_case_id, run)
    return latest


def _latest_run_summary(run: TestRun | None) -> TestbedLatestRunSummary | None:
    if run is None:
        return None
    return TestbedLatestRunSummary(
        id=run.id,
        status=run.status,
        result_summary=run.result_summary,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def build_testbed_readiness(
    *,
    agent: Agent,
    test_cases: list[TestCase],
    test_runs: list[TestRun],
) -> TestbedReadinessResponse:
    failures = evaluate_testbed_publish_gate(agent=agent, test_cases=test_cases, test_runs=test_runs)
    failure_by_case = {failure.test_case_id: failure for failure in failures if failure.test_case_id is not None}
    latest_by_case = _latest_run_by_case(test_runs)

    cases: list[TestbedCaseReadiness] = []
    passing_cases = 0
    failing_cases = 0
    running_cases = 0
    stale_cases = 0
    missing_run_cases = 0

    for test_case in sorted(test_cases, key=lambda candidate: candidate.created_at):
        latest_run = latest_by_case.get(test_case.id)
        failure = failure_by_case.get(test_case.id)

        if latest_run is None:
            missing_run_cases += 1
            case_status = "missing_run"
            required_action = "Run this scenario before publishing."
        elif failure and failure.code == "stale_run":
            stale_cases += 1
            case_status = "stale_run"
            required_action = "Re-run this scenario after the latest agent or scenario change."
        elif latest_run.status == TestCaseStatus.passed:
            passing_cases += 1
            case_status = "passed"
            required_action = None
        elif latest_run.status == TestCaseStatus.running:
            running_cases += 1
            case_status = "running"
            required_action = "Wait for the running Testbed execution to finish."
        else:
            failing_cases += 1
            case_status = "failed"
            required_action = "Fix the agent or scenario and run this case again."

        cases.append(
            TestbedCaseReadiness(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                status=case_status,
                latest_run=_latest_run_summary(latest_run),
                required_action=required_action,
            )
        )

    total_cases = len(test_cases)
    pass_rate = passing_cases / total_cases if total_cases else 0.0
    status = "ready" if total_cases >= MINIMUM_TEST_CASES and pass_rate >= REQUIRED_PASS_RATE and not failures else "action_required"

    return TestbedReadinessResponse(
        agent_id=agent.id,
        checked_at=datetime.now(UTC),
        status=status,
        publish_blocked=status != "ready",
        required_pass_rate=REQUIRED_PASS_RATE,
        minimum_test_cases=MINIMUM_TEST_CASES,
        total_cases=total_cases,
        passing_cases=passing_cases,
        failing_cases=failing_cases,
        running_cases=running_cases,
        stale_cases=stale_cases,
        missing_run_cases=missing_run_cases,
        pass_rate=pass_rate,
        failures=[failure.to_api_detail() for failure in failures],
        cases=cases,
    )
