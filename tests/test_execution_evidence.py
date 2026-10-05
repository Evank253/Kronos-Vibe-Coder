import sys

from backend.execution.contracts import ExecutionRequest
from backend.execution.evidence import collect_execution_evidence
from backend.execution.providers.local import LocalExecutionProvider


def test_evidence_binds_execution_commit_and_result_hash(tmp_path):
    request = ExecutionRequest(
        request_id="req-evidence",
        mission_id="mission-evidence",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=(sys.executable, "-c", "print('evidence')"),
    )
    result = LocalExecutionProvider().execute(request)
    evidence = collect_execution_evidence(result)

    assert evidence["execution_id"] == result.execution_id
    assert evidence["target_commit"] == "abc123"
    assert evidence["result_hash"]
    assert evidence["qualification_status"] == "NOT_QUALIFIED"


def test_failed_execution_remains_failure_evidence(tmp_path):
    request = ExecutionRequest(
        request_id="req-failure",
        mission_id="mission-failure",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=(sys.executable, "-c", "import sys; sys.exit(3)"),
        inputs={"phase": "build"},
    )
    result = LocalExecutionProvider().execute(request)
    evidence = collect_execution_evidence(result)

    assert evidence["status"] == "FAILED"
    assert evidence["failure_class"] == "BUILD_FAILED"
    assert evidence["qualification_status"] == "NOT_QUALIFIED"
