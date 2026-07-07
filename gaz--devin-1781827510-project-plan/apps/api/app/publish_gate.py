from dataclasses import dataclass
from uuid import UUID

from app.schemas import Agent, TestCase, TestCaseStatus, TestRun


@dataclass(frozen=True)
class PublishGateFailure:
    code: str
    message: str
    test_case_id: UUID | None = None
    test_case_name: str | None = None
    latest_run_id: UUID | None = None
    latest_run_status: TestCaseStatus | None = None

    def to_api_detail(self) -> dict[str, str]:
        detail = {
            "code": self.code,
            "message": self.message,
        }
        if self.test_case_id is not None:
            detail["test_case_id"] = str(self.test_case_id)
        if self.test_case_name is not None:
            detail["test_case_name"] = self.test_case_name
        if self.latest_run_id is not None:
            detail["latest_run_id"] = str(self.latest_run_id)
        if self.latest_run_status is not None:
            detail["latest_run_status"] = self.latest_run_status.value
        return detail


def evaluate_testbed_publish_gate(
    *,
    agent: Agent,
    test_cases: list[TestCase],
    test_runs: list[TestRun],
) -> list[PublishGateFailure]:
    if not test_cases:
        return [
            PublishGateFailure(
                code="no_test_cases",
                message="Add at least one Testbed scenario before publishing the agent.",
            )
        ]

    latest_run_by_case: dict[UUID, TestRun] = {}
    for run in sorted(
        test_runs,
        key=lambda candidate: (candidate.updated_at, candidate.created_at),
        reverse=True,
    ):
        latest_run_by_case.setdefault(run.test_case_id, run)

    failures: list[PublishGateFailure] = []
    for test_case in sorted(test_cases, key=lambda candidate: candidate.created_at):
        latest_run = latest_run_by_case.get(test_case.id)
        if latest_run is None:
            failures.append(
                PublishGateFailure(
                    code="missing_run",
                    message="Run this Testbed scenario before publishing.",
                    test_case_id=test_case.id,
                    test_case_name=test_case.name,
                )
            )
            continue

        if latest_run.updated_at < agent.updated_at or latest_run.updated_at < test_case.updated_at:
            failures.append(
                PublishGateFailure(
                    code="stale_run",
                    message="Re-run this Testbed scenario after the latest agent or scenario change.",
                    test_case_id=test_case.id,
                    test_case_name=test_case.name,
                    latest_run_id=latest_run.id,
                    latest_run_status=latest_run.status,
                )
            )
            continue

        if latest_run.status != TestCaseStatus.passed:
            failures.append(
                PublishGateFailure(
                    code=f"latest_run_{latest_run.status.value}",
                    message="The latest Testbed run for this scenario must pass before publishing.",
                    test_case_id=test_case.id,
                    test_case_name=test_case.name,
                    latest_run_id=latest_run.id,
                    latest_run_status=latest_run.status,
                )
            )

    return failures
