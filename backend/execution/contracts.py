"""MANIFEX-bound execution contracts for Kronos.

The contract is deliberately provider-neutral. Providers report facts; MANIFEX
performs qualification and authority decisions.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProviderPolicy:
    requested: str = "local"
    fallback_allowed: bool = False
    approved_fallbacks: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    mission_id: str
    repository: str
    commit_sha: str
    environment: Mapping[str, Any]
    command: Tuple[str, ...]
    inputs: Mapping[str, Any] = field(default_factory=dict)
    expected_result: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    resource_limits: Mapping[str, Any] = field(default_factory=dict)
    authority_class: str = "A"
    evidence_requirement: str = "E2"
    provenance_requirement: str = "required"
    provider_policy: ProviderPolicy = field(default_factory=ProviderPolicy)

    def __post_init__(self) -> None:
        if not self.request_id or not self.mission_id:
            raise ValueError("request_id and mission_id are required")
        if not self.repository or not self.commit_sha:
            raise ValueError("repository and commit_sha are required")
        if not self.command:
            raise ValueError("command is required")
        if self.authority_class not in {"A", "B", "C"}:
            raise ValueError("authority_class must be A, B, or C")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    request_id: str
    mission_id: str
    provider: str
    provider_run_id: Optional[str]
    status: str
    target_commit: str
    environment: Mapping[str, Any]
    started_at: str
    finished_at: str
    execution_started: bool
    exit_code: Optional[int]
    stdout: str = ""
    stderr: str = ""
    artifacts: Tuple[Mapping[str, Any], ...] = ()
    artifact_hashes: Mapping[str, str] = field(default_factory=dict)
    failure_class: Optional[str] = None
    evidence_id: Optional[str] = None
    qualification_status: str = "NOT_QUALIFIED"

    def __post_init__(self) -> None:
        if self.status not in {
            "EXECUTED", "FAILED", "BLOCKED", "NOT_MEASURED"
        }:
            raise ValueError("invalid execution status")
        if not self.execution_id or not self.request_id:
            raise ValueError("execution_id and request_id are required")
