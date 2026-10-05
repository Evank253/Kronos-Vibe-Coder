"""MANIFEX evidence-registration boundary.

This adapter validates and packages Kronos execution evidence for MANIFEX.
It does not qualify evidence, authorize actions, or mutate MANIFEX state.
"""
from typing import Any, Dict, Mapping

REQUIRED_FIELDS = (
    "evidence_id", "execution_id", "request_id", "mission_id",
    "repository", "target_commit", "provider", "phase", "command",
    "request_hash", "result_hash", "evidence_hash",
    "status", "execution_started", "qualification_status",
)

ALLOWED_QUALIFICATION_STATUS = {"NOT_QUALIFIED", "NOT_MEASURED"}


class ManifexRegistrationError(ValueError):
    """Evidence cannot be safely registered."""


def validate_registration_record(evidence: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in evidence]
    if missing:
        raise ManifexRegistrationError(
            "missing required evidence fields: " + ", ".join(missing)
        )
    if evidence["qualification_status"] not in ALLOWED_QUALIFICATION_STATUS:
        raise ManifexRegistrationError(
            "Kronos may only register unqualified/unmeasured evidence"
        )
    if not evidence["evidence_id"] or not evidence["execution_id"]:
        raise ManifexRegistrationError("evidence identity is required")
    if not evidence["target_commit"]:
        raise ManifexRegistrationError("target commit is required")
    if not isinstance(evidence["command"], list) or not evidence["command"]:
        raise ManifexRegistrationError("exact command must be a non-empty list")
    for name in ("request_hash", "result_hash", "evidence_hash"):
        value = evidence[name]
        if not isinstance(value, str) or len(value) != 64:
            raise ManifexRegistrationError(name + " must be a SHA-256 hex digest")
        try:
            int(value, 16)
        except ValueError as exc:
            raise ManifexRegistrationError(name + " must be hexadecimal") from exc


def build_registration_packet(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a transport-neutral packet for MANIFEX registration."""
    validate_registration_record(evidence)
    return {
        "schema": "manifex-execution-evidence/v1",
        "source": "Kronos-Vibe-Coder",
        "evidence": dict(evidence),
        "qualification_requested": False,
        "authority_decision_requested": False,
    }
