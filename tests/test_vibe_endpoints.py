import time

from fastapi.testclient import TestClient

from backend.main import app
from backend.vibe_endpoints import TASK_MANAGER


client = TestClient(app)


def test_scan_and_fix_status_and_merge(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "sample.py").write_text("def demo():\n\treturn 1  \n")
    csrf_token = client.get("/whoami").json()["csrf_token"]

    response = client.post(
        "/vibe/scan-and-fix",
        json={"path": str(project)},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"]

    deadline = time.time() + 5
    status_payload = None
    while time.time() < deadline:
        status_response = client.get(f"/vibe/status/{payload['task_id']}")
        status_payload = status_response.json()
        if status_payload["status"] in {"completed", "completed_with_errors", "failed"}:
            break
        time.sleep(0.1)

    assert status_payload is not None
    assert status_payload["status"] in {"completed", "completed_with_errors"}

    merge_response = client.post(
        "/vibe/merge-results",
        json={"task_id": payload["task_id"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert merge_response.status_code == 200
    assert "merged_result" in merge_response.json()


def test_vibe_websocket_stream(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "sample.py").write_text("def demo():\n\treturn 1  \n")
    task = TASK_MANAGER.create_task(str(project))

    with client.websocket_connect(f"/vibe/updates/{task['task_id']}") as websocket:
        payload = websocket.receive_json()

    assert payload["task_id"] == task["task_id"]
