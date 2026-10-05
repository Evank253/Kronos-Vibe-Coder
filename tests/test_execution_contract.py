import sys

import pytest

from backend.execution.contracts import ExecutionRequest
from backend.execution.providers.local import LocalExecutionProvider


def request(tmp_path, command, timeout=5, phase="execute"):
    return ExecutionRequest(
        request_id="req-001",
        mission_id="mission-001",
        repository="example/repo",
        commit_sha="abc123",
        environment={"cwd": str(tmp_path)},
        command=tuple(command),
        inputs={"phase": phase},
        timeout_seconds=timeout,
    )


def test_valid_execution_is_identified_and_hashed(tmp_path):
    result = LocalExecutionProvider().execute(
        request(tmp_path, [sys.executable, "-c", "print('ok')"])
    )
    assert result.status == "EXECUTED"
    assert result.execution_started is True
    assert result.exit_code == 0
    assert result.artifact_hashes["stdout_sha256"]
    assert result.target_commit == "abc123"


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("test", "TEST_FAILED"),
        ("build", "BUILD_FAILED"),
        ("deploy", "DEPLOY_FAILED"),
        ("execute", "EXECUTION_FAILED"),
    ],
)
def test_nonzero_exit_is_classified_by_phase(tmp_path, phase, expected):
    result = LocalExecutionProvider().execute(
        request(
            tmp_path,
            [sys.executable, "-c", "import sys; sys.exit(2)"],
            phase=phase,
        )
    )
    assert result.status == "FAILED"
    assert result.failure_class == expected


def test_timeout_is_typed(tmp_path):
    result = LocalExecutionProvider().execute(
        request(tmp_path, [sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
    )
    assert result.status == "FAILED"
    assert result.execution_started is True
    assert result.failure_class == "TIMEOUT"


def test_missing_command_is_runner_unavailable(tmp_path):
    result = LocalExecutionProvider().execute(
        request(tmp_path, ["definitely-not-a-real-command"])
    )
    assert result.status == "NOT_MEASURED"
    assert result.execution_started is False
    assert result.failure_class == "RUNNER_UNAVAILABLE"


def test_contract_rejects_missing_commit(tmp_path):
    with pytest.raises(ValueError):
        ExecutionRequest(
            request_id="req-001",
            mission_id="mission-001",
            repository="example/repo",
            commit_sha="",
            environment={"cwd": str(tmp_path)},
            command=("echo", "ok"),
        )
