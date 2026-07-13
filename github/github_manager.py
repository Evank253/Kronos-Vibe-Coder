from github import Github


def get_repo_info(token, repo_name):
    gh = Github(token)
    repo = gh.get_repo(repo_name)
    return {
        "name": repo.full_name,
        "description": repo.description,
        "private": repo.private,
        "url": repo.html_url
    }
