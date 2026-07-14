"""
File Analysis Engine
Scans extracted files for structure, identifies types, extracts imports,
and generates architecture maps and file-relationship data.
"""
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


# Mapping of file extensions to language labels
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".sol": "Solidity",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".html": "HTML",
    ".css": "CSS",
    ".sh": "Shell",
    ".dockerfile": "Dockerfile",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".rb": "Ruby",
}

# Files recognised as configuration
CONFIG_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env",
    ".env.example",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "requirements.txt",
    "pipfile",
    ".flake8",
    ".gitignore",
}

# Regex for Python import statements (fallback for files with syntax errors)
_PY_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)

# Regex for Solidity import paths
_SOL_IMPORT_RE = re.compile(r'import\s+["\']([^"\']+)["\']')

# Regexes for JavaScript/TypeScript imports and requires
_JS_IMPORT_PATTERNS = [
    re.compile(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'),
    re.compile(r'from\s+["\']([^"\']+)["\']'),
    re.compile(r'import\s+["\']([^"\']+)["\']'),
]


def detect_language(file_path: Path) -> str:
    """Return the language/type label for a file."""
    name_lower = file_path.name.lower()
    if name_lower in CONFIG_FILENAMES:
        return "Config"
    if name_lower == "dockerfile":
        return "Dockerfile"
    ext = file_path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def extract_python_imports(source: str) -> List[str]:
    """Parse a Python source string and return a list of imported module names."""
    imports = []
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
    except SyntaxError:
        # Fall back to regex for files with syntax errors
        for match in _PY_IMPORT_RE.finditer(source):
            imports.append(match.group(1))
    return sorted(set(imports))


def extract_solidity_imports(source: str) -> List[str]:
    """Return a list of paths/modules imported in a Solidity file."""
    return _SOL_IMPORT_RE.findall(source)


def extract_js_imports(source: str) -> List[str]:
    """Return a list of modules required/imported in a JS/TS file."""
    imports = []
    for pattern in _JS_IMPORT_PATTERNS:
        imports.extend(pattern.findall(source))
    return sorted(set(imports))


def _read_safe(file_path: Path, max_bytes: int = 512 * 1024) -> Optional[str]:
    """Read a text file up to *max_bytes* bytes; return None on failure."""
    try:
        raw = file_path.read_bytes()[:max_bytes]
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def analyze_file(file_path: Path) -> Dict:
    """
    Analyse a single file and return a structured summary.

    Returns a dict with keys: path, language, size_bytes, imports, is_binary.
    """
    language = detect_language(file_path)
    size = file_path.stat().st_size if file_path.exists() else 0

    result: Dict = {
        "path": str(file_path),
        "language": language,
        "size_bytes": size,
        "imports": [],
        "is_binary": False,
    }

    source = _read_safe(file_path)
    if source is None:
        result["is_binary"] = True
        return result

    if language == "Python":
        result["imports"] = extract_python_imports(source)
    elif language == "Solidity":
        result["imports"] = extract_solidity_imports(source)
    elif language in ("JavaScript", "TypeScript"):
        result["imports"] = extract_js_imports(source)

    return result


def analyze_directory(root: str) -> Dict:
    """
    Recursively scan *root* and return a full analysis report.

    Returns:
        Dict with keys: root, total_files, language_distribution,
        files (list of per-file analysis dicts), dependency_graph.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    file_analyses: List[Dict] = []
    language_counts: Dict[str, int] = {}

    for file_path in sorted(root_path.rglob("*")):
        if not file_path.is_file():
            continue
        analysis = analyze_file(file_path)
        # Use path relative to root for readability
        try:
            analysis["path"] = str(file_path.relative_to(root_path))
        except ValueError:
            pass
        file_analyses.append(analysis)
        lang = analysis["language"]
        language_counts[lang] = language_counts.get(lang, 0) + 1

    # Build a simple dependency graph: {file: [imported_modules]}
    dependency_graph: Dict[str, List[str]] = {}
    for fa in file_analyses:
        if fa["imports"]:
            dependency_graph[fa["path"]] = fa["imports"]

    return {
        "root": str(root_path),
        "total_files": len(file_analyses),
        "language_distribution": language_counts,
        "files": file_analyses,
        "dependency_graph": dependency_graph,
    }


def generate_architecture_map(analysis: Dict) -> Dict:
    """
    Generate a high-level architecture map from an analysis report.

    Groups files by language and identifies key entry-points.
    """
    by_language: Dict[str, List[str]] = {}
    for fa in analysis.get("files", []):
        lang = fa["language"]
        by_language.setdefault(lang, []).append(fa["path"])

    entry_points = [
        fa["path"]
        for fa in analysis.get("files", [])
        if fa["path"].endswith("main.py")
        or fa["path"].endswith("app.py")
        or fa["path"].endswith("index.js")
        or fa["path"].endswith("index.ts")
    ]

    return {
        "files_by_language": by_language,
        "entry_points": entry_points,
        "dependency_graph": analysis.get("dependency_graph", {}),
        "total_files": analysis.get("total_files", 0),
        "language_distribution": analysis.get("language_distribution", {}),
    }


def save_analysis_report(analysis: Dict, output_path: str) -> str:
    """Serialise *analysis* to a JSON file at *output_path*."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(analysis, indent=2))
    return str(out)
