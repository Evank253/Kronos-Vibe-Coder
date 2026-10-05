import sys

import pytest

from backend.execution.contracts import ExecutionRequest
from backend.execution.evidence import collect_execution_evidence
from backend.execution.providers.local import LocalExecutionProvider
from backend.integration.manifex_registration import (
    ManifexRegistrationError,
    build_registration_packet,
)


def evidence(tmp_path):
    request = ExecutionRequest(
        request_id="req-register",
        mission_id="mission-register",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=(sys.executable, "-c", "print('register')"),
        inputs={"phase": "test"},
        expected_result={"exit_code": 0},
    )
    return collect_execution_evidence(request, LocalExecutionProvider().execute(request))


def test_registration_preserves_evidence_without_qualification(tmp_path):
    packet = build_registration_packet(evidence(tmp_path))
    assert packet["schema"] == "manifex-execution-evidence/v1"
    assert packet["qualification_requested"] is False
    assert packet["authority_decision_requested"] is False
    assert packet["evidence"]["qualification_status"] == "NOT_QUALIFIED"


def test_registration_rejects_qualified_claims(tmp_path):
    record = evidence(tmp_path)
    record["qualification_status"] = "QUALIFIED"
    with pytest.raises(ManifexRegistrationError):
        build_registration_packet(record)


def test_registration_rejects_missing_provenance(tmp_path):
    record = evidence(tmp_path)
    del record["target_commit"]
    with pytest.raises(ManifexRegistrationError):
        build_registration_packet(record)


def test_registration_rejects_invalid_hash(tmp_path):
    record = evidence(tmp_path)
    record["evidence_hash"] = "not-a-sha256"
    with pytest.raises(ManifexRegistrationError):
        build_registration_packet(record)
