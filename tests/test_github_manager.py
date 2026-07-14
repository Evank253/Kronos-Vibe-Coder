from unittest.mock import MagicMock, patch

from backend.agents import github_manager


@patch("backend.agents.github_manager.Github")
def test_create_branch_existing(mock_gh_class):
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    mock_repo.get_branch.return_value = MagicMock()
    # get_git_ref raises to indicate ref does not exist
    mock_repo.get_git_ref.side_effect = Exception("not found")
    mock_gh_class.return_value = mock_gh

    resp = github_manager.create_branch(
        "owner/repo", "new-branch", base_branch="main", token="tok"
    )
    assert resp["status"] in ("branch_created", "exists")


@patch("backend.agents.github_manager.Github")
def test_commit_changes_create_update(mock_gh_class):
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    # Simulate file not found then created
    mock_repo.get_contents.side_effect = Exception("not found")
    mock_repo.create_file.return_value = {"commit": {"sha": "abc123"}}
    mock_gh_class.return_value = mock_gh

    changes = [{"path": "a.txt", "content": "hello"}]
    resp = github_manager.commit_changes(
        "owner/repo", "branch", "msg", changes, token="tok"
    )
    assert resp["status"] == "committed"
    assert resp["changes"][0]["action"] == "created"


@patch("backend.agents.github_manager.Github")
def test_open_pr(mock_gh_class):
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    pr = MagicMock()
    pr.number = 1
    pr.html_url = "http://pr"
    mock_repo.create_pull.return_value = pr
    mock_gh.get_repo.return_value = mock_repo
    mock_gh_class.return_value = mock_gh

    resp = github_manager.open_pull_request(
        "owner/repo", "title", "body", "head", base="main", token="tok"
    )
    assert resp["status"] == "pull_request_opened"
