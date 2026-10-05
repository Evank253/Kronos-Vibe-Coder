"""Build immutable-shaped execution evidence without qualifying it."""
import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict

from .contracts import ExecutionRequest, ExecutionResult


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def collect_execution_evidence(
    request: ExecutionRequest, result: ExecutionResult
) -> Dict[str, Any]:
    """Bind the execution request and result into one evidence record.

    This function records facts only. Qualification remains a MANIFEX decision.
    """
    request_payload = asdict(request)
    result_payload = asdict(result)
    evidence = {
        "evidence_id": "exec-" + result.execution_id,
        "execution_id": result.execution_id,
        "request_id": request.request_id,
        "mission_id": request.mission_id,
        "repository": request.repository,
        "target_commit": request.commit_sha,
        "provider": result.provider,
        "provider_run_id": result.provider_run_id,
        "phase": str(request.inputs.get("phase", "execute")).lower(),
        "command": list(request.command),
        "inputs": dict(request.inputs),
        "expected_result": dict(request.expected_result),
        "timeout_seconds": request.timeout_seconds,
        "resource_limits": dict(request.resource_limits),
        "authority_class": request.authority_class,
        "evidence_requirement": request.evidence_requirement,
        "provenance_requirement": request.provenance_requirement,
        "provider_policy": asdict(request.provider_policy),
        "environment": dict(result.environment),
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "execution_started": result.execution_started,
        "status": result.status,
        "exit_code": result.exit_code,
        "failure_class": result.failure_class,
        "stdout_sha256": result.artifact_hashes.get("stdout_sha256"),
        "stderr_sha256": result.artifact_hashes.get("stderr_sha256"),
        "request_hash": canonical_hash(request_payload),
        "result_hash": canonical_hash(result_payload),
        "evidence_hash": None,
        "diagnostics": {
            "stdout_present": bool(result.stdout),
            "stderr_present": bool(result.stderr),
        },
        "qualification_status": "NOT_QUALIFIED",
    }
    hash_input = {k: v for k, v in evidence.items() if k != "evidence_hash"}
    evidence["evidence_hash"] = canonical_hash(hash_input)
    return evidence
