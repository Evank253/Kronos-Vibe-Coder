#!/usr/bin/env python3
"""
Run Vibe Developer -> Vibe Coder handshake for Kronos-Vibe-Coder.

Order enforced:
  1. Wait for Vibe Developer to publish its dependency contract.
  2. Align requirements.txt to the published pins.
  3. Install the aligned dependencies.
  4. Run the test suite as a smoke check.
  5. Acknowledge the Developer with what was implemented + smoke result.
  6. If the smoke check passed and requirements.txt changed, commit it.

Exit code is non-zero if the Developer never publishes, or if the smoke
check fails — this is meant to be used as a CI/Codespaces gate before push.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.vibe_developer_bridge import (  # noqa: E402
    DeveloperNotReadyError,
    acknowledge_coder,
    align_requirements,
    report_smoke,
    wait_for_developer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = REPO_ROOT / "requirements.txt"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=REPO_ROOT, **kwargs)


def main() -> int:
    print("[align] waiting for Vibe Developer to publish dependency contract...")
    try:
        brief = wait_for_developer(timeout_seconds=120.0)
    except DeveloperNotReadyError as exc:
        print(f"[align] FAILED: {exc}", file=sys.stderr)
        return 1

    pins = brief["pins"]
    print(f"[align] developer contract received: {pins}")

    changed = align_requirements(pins, REQUIREMENTS)
    if changed:
        print(f"[align] requirements.txt updated to match developer pins: {changed}")
    else:
        print("[align] requirements.txt already matches developer pins")

    install = run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    if install.returncode != 0:
        report_smoke(False, detail="pip install failed after dependency alignment")
        return install.returncode

    print("[align] running smoke tests (pytest)...")
    test = run([sys.executable, "-m", "pytest", "-q"])
    smoke_ok = test.returncode == 0

    acknowledge_coder(
        implemented=["dependency alignment with Vibe Developer contract"],
        blockers=[] if smoke_ok else ["pytest failed after alignment"],
    )
    report_smoke(smoke_ok, detail="pytest -q" if smoke_ok else "pytest -q failed")

    if not smoke_ok:
        print("[align] FAILED: smoke tests did not pass, not committing", file=sys.stderr)
        return test.returncode

    if changed:
        run(["git", "add", "requirements.txt"])
        diff = run(["git", "diff", "--cached", "--quiet"])
        if diff.returncode != 0:  # there is something staged
            run(
                [
                    "git",
                    "-c",
                    "user.email=vibe-coder@users.noreply.github.com",
                    "-c",
                    "user.name=Vibe Coder (auto-align)",
                    "commit",
                    "-m",
                    "chore(deps): align dependencies with Vibe Developer contract",
                ]
            )
            print("[align] committed dependency alignment. Push it from CI/Codespaces once ready.")

    print("[align] OK — developer and coder are aligned, smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
