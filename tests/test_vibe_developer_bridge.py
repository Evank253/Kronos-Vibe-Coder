from unittest.mock import MagicMock, patch

import pytest

from backend import vibe_developer_bridge as bridge


# ---------------------------------------------------------------------------
# align_requirements — pure function, no network needed
# ---------------------------------------------------------------------------


def test_align_requirements_pins_existing_unpinned_packages(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi\nuvicorn\nrequests\n", encoding="utf-8")

    pins = {"fastapi": "0.115.0", "uvicorn": "0.30.6"}
    changed = bridge.align_requirements(pins, req)

    content = req.read_text(encoding="utf-8")
    assert "fastapi==0.115.0" in content
    assert "uvicorn==0.30.6" in content
    assert "requests" in content  # untouched, no pin given
    assert set(changed) == {"fastapi==0.115.0", "uvicorn==0.30.6"}


def test_align_requirements_repins_wrong_version(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.100.0\n", encoding="utf-8")

    changed = bridge.align_requirements({"fastapi": "0.115.0"}, req)

    assert req.read_text(encoding="utf-8").strip() == "fastapi==0.115.0"
    assert changed == ["fastapi==0.115.0"]


def test_align_requirements_noop_when_already_aligned(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.115.0\n", encoding="utf-8")

    changed = bridge.align_requirements({"fastapi": "0.115.0"}, req)

    assert changed == []
    assert req.read_text(encoding="utf-8").strip() == "fastapi==0.115.0"


def test_align_requirements_appends_missing_pin(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests\n", encoding="utf-8")

    changed = bridge.align_requirements({"pydantic": "2.9.2"}, req)

    content = req.read_text(encoding="utf-8")
    assert "requests" in content
    assert "pydantic==2.9.2" in content
    assert changed == ["pydantic==2.9.2"]


def test_align_requirements_creates_file_if_missing(tmp_path):
    req = tmp_path / "requirements.txt"
    assert not req.exists()

    changed = bridge.align_requirements({"fastapi": "0.115.0"}, req)

    assert req.exists()
    assert req.read_text(encoding="utf-8").strip() == "fastapi==0.115.0"
    assert changed == ["fastapi==0.115.0"]


# ---------------------------------------------------------------------------
# wait_for_developer / get_brief — HTTP mocked
# ---------------------------------------------------------------------------


@patch("backend.vibe_developer_bridge.requests.get")
def test_wait_for_developer_returns_immediately_when_ready(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ready": True, "pins": {"fastapi": "0.115.0"}}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    brief = bridge.wait_for_developer(base_url="http://fake:4000", timeout_seconds=5)

    assert brief["ready"] is True
    mock_get.assert_called_once()


@patch("backend.vibe_developer_bridge.time.sleep", return_value=None)
@patch("backend.vibe_developer_bridge.requests.get")
def test_wait_for_developer_times_out_when_never_ready(mock_get, _mock_sleep):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ready": False}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    with pytest.raises(bridge.DeveloperNotReadyError):
        bridge.wait_for_developer(base_url="http://fake:4000", timeout_seconds=0.01, poll_seconds=0.01)


# ---------------------------------------------------------------------------
# acknowledge_coder / report_smoke — HTTP mocked
# ---------------------------------------------------------------------------


@patch("backend.vibe_developer_bridge.requests.post")
def test_acknowledge_coder_posts_expected_payload(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    result = bridge.acknowledge_coder(
        implemented=["thing a"], blockers=["thing b"], base_url="http://fake:4000"
    )

    assert result == {"ok": True}
    args, kwargs = mock_post.call_args
    assert args[0] == "http://fake:4000/api/vibe/coder"
    assert kwargs["json"] == {"implemented": ["thing a"], "blockers": ["thing b"]}


@patch("backend.vibe_developer_bridge.requests.post")
def test_report_smoke_posts_expected_payload(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    bridge.report_smoke(True, detail="all good", base_url="http://fake:4000")

    args, kwargs = mock_post.call_args
    assert args[0] == "http://fake:4000/api/vibe/smoke"
    assert kwargs["json"] == {"ok": True, "detail": "all good"}
