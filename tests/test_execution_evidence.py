import sys

from backend.execution.contracts import ExecutionRequest
from backend.execution.evidence import collect_execution_evidence
from backend.execution.providers.local import LocalExecutionProvider


def test_evidence_binds_request_and_result(tmp_path):
    request = ExecutionRequest(
        request_id="req-evidence",
        mission_id="mission-evidence",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=(sys.executable, "-c", "print('evidence')"),
        inputs={"phase": "test", "fixture": "fixture-001"},
        expected_result={"exit_code": 0},
        resource_limits={"cpu_seconds": 10},
    )
    result = LocalExecutionProvider().execute(request)
    evidence = collect_execution_evidence(request, result)

    assert evidence["execution_id"] == result.execution_id
    assert evidence["request_id"] == request.request_id
    assert evidence["mission_id"] == request.mission_id
    assert evidence["repository"] == request.repository
    assert evidence["target_commit"] == request.commit_sha
    assert evidence["phase"] == "test"
    assert evidence["command"] == list(request.command)
    assert evidence["expected_result"] == {"exit_code": 0}
    assert evidence["request_hash"]
    assert evidence["result_hash"]
    assert evidence["evidence_hash"]
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
    evidence = collect_execution_evidence(request, result)

    assert evidence["status"] == "FAILED"
    assert evidence["failure_class"] == "BUILD_FAILED"
    assert evidence["qualification_status"] == "NOT_QUALIFIED"


def test_request_change_changes_request_hash(tmp_path):
    provider = LocalExecutionProvider()
    command = (sys.executable, "-c", "print('same-result')")
    first = ExecutionRequest(
        request_id="req-a", mission_id="mission-a", repository="example/repo",
        commit_sha="abc123", environment={"cwd": str(tmp_path)}, command=command,
        expected_result={"exit_code": 0},
    )
    second = ExecutionRequest(
        request_id="req-b", mission_id="mission-b", repository="example/repo",
        commit_sha="abc123", environment={"cwd": str(tmp_path)}, command=command,
        expected_result={"exit_code": 0},
    )
    e1 = collect_execution_evidence(first, provider.execute(first))
    e2 = collect_execution_evidence(second, provider.execute(second))
    assert e1["request_hash"] != e2["request_hash"]
