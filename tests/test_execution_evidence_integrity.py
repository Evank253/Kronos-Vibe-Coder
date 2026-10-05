import sys

from backend.execution.contracts import ExecutionRequest
from backend.execution.evidence import canonical_hash, collect_execution_evidence
from backend.execution.providers.local import LocalExecutionProvider


def make_request(tmp_path):
    return ExecutionRequest(
        request_id="req-integrity",
        mission_id="mission-integrity",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=(sys.executable, "-c", "print('integrity')"),
        inputs={"phase": "test"},
        expected_result={"exit_code": 0},
        timeout_seconds=10,
        resource_limits={"cpu_seconds": 10},
    )


def test_evidence_hash_recomputes(tmp_path):
    request = make_request(tmp_path)
    result = LocalExecutionProvider().execute(request)
    evidence = collect_execution_evidence(request, result)
    unsigned = {k: v for k, v in evidence.items() if k != "evidence_hash"}
    assert evidence["evidence_hash"] == canonical_hash(unsigned)


def test_request_and_result_hashes_match_canonical_payloads(tmp_path):
    request = make_request(tmp_path)
    result = LocalExecutionProvider().execute(request)
    evidence = collect_execution_evidence(request, result)
    from dataclasses import asdict
    assert evidence["request_hash"] == canonical_hash(asdict(request))
    assert evidence["result_hash"] == canonical_hash(asdict(result))
