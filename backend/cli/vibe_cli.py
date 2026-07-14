from __future__ import annotations

import argparse
import json
import time
import webbrowser

from backend.agents.swarm.task_manager import SwarmTaskManager
from backend.codespace_adapter import dashboard_url, resolve_workspace_path


CLI_MANAGER = SwarmTaskManager()


def _wait_for_completion(task_id: str) -> dict:
    while True:
        task = CLI_MANAGER.get_task(task_id)
        if task and task["status"] in {"completed", "completed_with_errors", "failed"}:
            return task
        time.sleep(0.2)


def command_scan(args: argparse.Namespace) -> int:
    task = CLI_MANAGER.create_task(str(resolve_workspace_path(args.path)))
    result = _wait_for_completion(task["task_id"])
    print(json.dumps(result, indent=2))
    return 0


def command_fix(args: argparse.Namespace) -> int:
    task = CLI_MANAGER.create_task(str(resolve_workspace_path(args.path)))
    result = _wait_for_completion(task["task_id"])
    merged = CLI_MANAGER.finalize(task["task_id"], write_files=True)
    print(json.dumps({"task": result, "merge": merged}, indent=2))
    return 0


def command_deploy(args: argparse.Namespace) -> int:
    payload = {
        "target": args.repo,
        "status": "ready",
        "message": "Connect this payload to the existing GitHub deployment flow for PR creation.",
    }
    print(json.dumps(payload, indent=2))
    return 0


def command_dashboard(args: argparse.Namespace) -> int:
    url = dashboard_url()
    webbrowser.open(url)
    print(url)
    return 0


def command_watch(args: argparse.Namespace) -> int:
    task = CLI_MANAGER.create_task(str(resolve_workspace_path(args.path)))
    while True:
        snapshot = CLI_MANAGER.get_task(task["task_id"])
        print(json.dumps(snapshot["summary"], indent=2))
        if snapshot["status"] in {"completed", "completed_with_errors", "failed"}:
            return 0
        time.sleep(0.5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vibe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan")
    scan.add_argument("path", nargs="?", default=".")
    scan.set_defaults(func=command_scan)

    fix = subparsers.add_parser("fix")
    fix.add_argument("path", nargs="?", default=".")
    fix.set_defaults(func=command_fix)

    deploy = subparsers.add_parser("deploy")
    deploy.add_argument("repo")
    deploy.set_defaults(func=command_deploy)

    dashboard = subparsers.add_parser("dashboard")
    dashboard.set_defaults(func=command_dashboard)

    watch = subparsers.add_parser("watch")
    watch.add_argument("path", nargs="?", default=".")
    watch.set_defaults(func=command_watch)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
