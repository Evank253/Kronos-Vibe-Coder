"""Local execution provider wrapping Kronos's existing subprocess model."""
import hashlib
import subprocess
import uuid
from datetime import datetime, timezone

from ..contracts import ExecutionResult
from ..environment import capture_environment
from ..failure import classify_nonzero_exit


def _now():
    return datetime.now(timezone.utc).isoformat()


class LocalExecutionProvider:
    name = "local"

    def health(self):
        return {"provider": self.name, "available": True}

    def execute(self, request):
        execution_id = str(uuid.uuid4())
        started = _now()
        environment = dict(capture_environment())
        phase = str(request.inputs.get("phase", "execute")).lower()
        try:
            completed = subprocess.run(
                list(request.command),
                cwd=request.environment.get("cwd") or None,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                check=False,
            )
            finished = _now()
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            status = "EXECUTED" if completed.returncode == 0 else "FAILED"
            failure = None if completed.returncode == 0 else classify_nonzero_exit(phase)
            hashes = {
                "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            }
            return ExecutionResult(
                execution_id=execution_id,
                request_id=request.request_id,
                mission_id=request.mission_id,
                provider=self.name,
                provider_run_id=execution_id,
                status=status,
                target_commit=request.commit_sha,
                environment=environment,
                started_at=started,
                finished_at=finished,
                execution_started=True,
                exit_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                artifact_hashes=hashes,
                failure_class=failure,
            )
        except subprocess.TimeoutExpired as exc:
            finished = _now()
            stdout = (exc.stdout or "")
            stderr = (exc.stderr or "")
            return ExecutionResult(
                execution_id=execution_id,
                request_id=request.request_id,
                mission_id=request.mission_id,
                provider=self.name,
                provider_run_id=execution_id,
                status="FAILED",
                target_commit=request.commit_sha,
                environment=environment,
                started_at=started,
                finished_at=finished,
                execution_started=True,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                artifact_hashes={
                    "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
                    "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
                },
                failure_class="TIMEOUT",
            )
        except OSError as exc:
            finished = _now()
            return ExecutionResult(
                execution_id=execution_id,
                request_id=request.request_id,
                mission_id=request.mission_id,
                provider=self.name,
                provider_run_id=execution_id,
                status="NOT_MEASURED",
                target_commit=request.commit_sha,
                environment=environment,
                started_at=started,
                finished_at=finished,
                execution_started=False,
                exit_code=None,
                stderr=str(exc),
                failure_class="RUNNER_UNAVAILABLE",
            )
