from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


class SwarmExecutor:
    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers

    def run(self, jobs: list[tuple[str, Callable[[], Any]]]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {pool.submit(job): name for name, job in jobs}
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    results[name] = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    results[name] = {"status": "failed", "error": str(exc), "agent": name}
        return results
