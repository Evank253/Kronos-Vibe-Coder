"""Typed execution failures.

Infrastructure/provider failures are never converted into test pass/fail results.
"""
from dataclasses import dataclass
from typing import Optional


FAILURE_CLASSES = {
    "TEST_FAILED",
    "BUILD_FAILED",
    "DEPLOY_FAILED",
    "EXECUTION_FAILED",
    "RUNNER_UNAVAILABLE",
    "PROVIDER_BLOCKED",
    "BILLING_BLOCKED",
    "AUTHORIZATION_DENIED",
    "TIMEOUT",
    "DEPENDENCY_FAILURE",
    "INFRASTRUCTURE_FAILURE",
}


@dataclass(frozen=True)
class ExecutionFailure:
    failure_class: str
    phase: str
    provider: str
    provider_run_id: Optional[str]
    execution_started: bool
    infrastructure_state: str
    retryable: bool
    fallback_allowed: bool
    reason: str
    timestamp: str
    evidence_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_class not in FAILURE_CLASSES:
            raise ValueError(f"unknown failure class: {self.failure_class}")


def classify_nonzero_exit(phase: str) -> str:
    """Map a failed command to its declared execution phase."""
    return {
        "test": "TEST_FAILED",
        "build": "BUILD_FAILED",
        "deploy": "DEPLOY_FAILED",
    }.get(phase, "EXECUTION_FAILED")
