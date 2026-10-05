"""Build execution evidence from provider facts without qualifying them."""
import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict

from .contracts import ExecutionResult


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def collect_execution_evidence(result: ExecutionResult) -> Dict[str, Any]:
    """Create an attributable evidence record; qualification remains MANIFEX's job."""
    payload = asdict(result)
    evidence = {
        "evidence_id": "exec-" + result.execution_id,
        "execution_id": result.execution_id,
        "request_id": result.request_id,
        "mission_id": result.mission_id,
        "provider": result.provider,
        "provider_run_id": result.provider_run_id,
        "target_commit": result.target_commit,
        "environment": dict(result.environment),
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "execution_started": result.execution_started,
        "status": result.status,
        "exit_code": result.exit_code,
        "failure_class": result.failure_class,
        "result_hash": canonical_hash(payload),
        "stdout_sha256": result.artifact_hashes.get("stdout_sha256"),
        "stderr_sha256": result.artifact_hashes.get("stderr_sha256"),
        "qualification_status": "NOT_QUALIFIED",
    }
    return evidence
