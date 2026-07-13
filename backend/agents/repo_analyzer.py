from pathlib import Path


def analyze_repo(path):
    files = []
    for item in Path(path).rglob("*"):
        if item.is_file():
            files.append(str(item))

    return {
        "status": "analysis complete",
        "files_found": len(files),
        "files": files[:100]
    }
