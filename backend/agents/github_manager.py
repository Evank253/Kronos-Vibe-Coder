import os
from github import Github


def get_github_client(token=None):
    token = token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is required")
    return Github(token)


def create_branch(repo_full_name, branch_name, base_branch="main", token=None):
    gh = get_github_client(token)
    repo = gh.get_repo(repo_full_name)
    source_branch = repo.get_branch(base_branch)
    ref_name = f"refs/heads/{branch_name}"

    try:
        repo.get_git_ref(ref_name)
        return {
            "status": "exists",
            "branch": branch_name,
            "repo": repo_full_name,
        }
    except Exception:
        # If ref not found or any error when checking, attempt to create
        repo.create_git_ref(ref_name, source_branch.commit.sha)
        return {
            "status": "branch_created",
            "branch": branch_name,
            "base_branch": base_branch,
            "repo": repo_full_name,
        }


def commit_changes(
    repo_full_name, branch_name, commit_message, changes, token=None
):
    gh = get_github_client(token)
    repo = gh.get_repo(repo_full_name)
    results = []

    for change in changes:
        path = change["path"]
        content = change["content"]
        message = change.get("message", commit_message)

        def _commit_sha(obj):
            if hasattr(obj, "sha"):
                return getattr(obj, "sha")
            if isinstance(obj, dict):
                # Github.py sometimes returns nested dicts
                return obj.get("commit", {}).get("sha") or obj.get("sha")
            return None

        try:
            file_content = repo.get_contents(path, ref=branch_name)
            updated = repo.update_file(
                path,
                message,
                content,
                file_content.sha,
                branch=branch_name,
            )
            results.append(
                {
                    "path": path,
                    "action": "updated",
                    "commit": _commit_sha(
                        updated.get("commit")
                        if isinstance(updated, dict)
                        else updated
                    ),
                }
            )
        except Exception:
            # If file doesn't exist or another error occurred, create it
            created = repo.create_file(
                path,
                message,
                content,
                branch=branch_name,
            )
            results.append(
                {
                    "path": path,
                    "action": "created",
                    "commit": _commit_sha(
                        created.get("commit")
                        if isinstance(created, dict)
                        else created
                    ),
                }
            )

    return {
        "status": "committed",
        "repo": repo_full_name,
        "branch": branch_name,
        "changes": results,
    }


def open_pull_request(
    repo_full_name, title, body, head, base="main", token=None
):
    gh = get_github_client(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.create_pull(title=title, body=body, head=head, base=base)
    return {
        "status": "pull_request_opened",
        "repo": repo_full_name,
        "title": title,
        "number": pr.number,
        "url": pr.html_url,
        "head": head,
        "base": base,
    }
