"""
Integration Manager
Organises extracted files into categorised directories and generates
integration reports and dependency maps.
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from utils.file_analyzer import detect_language, analyze_directory, generate_architecture_map


# Maps language labels to target sub-directories
LANGUAGE_CATEGORY_MAP = {
    "Python": "python",
    "Solidity": "contracts",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Markdown": "docs",
    "JSON": "config",
    "YAML": "config",
    "TOML": "config",
    "HTML": "web",
    "CSS": "web",
    "Shell": "scripts",
    "Dockerfile": "docker",
    "Rust": "rust",
    "Go": "go",
    "Java": "java",
    "C++": "cpp",
    "C": "c",
    "Ruby": "ruby",
    "Config": "config",
    "Unknown": "misc",
}


class IntegrationManager:
    """Organise extracted files and produce integration reports."""

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)

    def categorize_files(self, copy: bool = False) -> Dict:
        """
        Walk *source_dir* and categorise each file by language.

        Args:
            copy: When True, copy files into categorised sub-directories
                  inside *target_dir*.  When False only report without
                  touching files.

        Returns:
            Dict mapping category names to lists of file paths.
        """
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        categories: Dict[str, List[str]] = {}

        for file_path in sorted(self.source_dir.rglob("*")):
            if not file_path.is_file():
                continue

            language = detect_language(file_path)
            category = LANGUAGE_CATEGORY_MAP.get(language, "misc")
            rel = str(file_path.relative_to(self.source_dir))
            categories.setdefault(category, []).append(rel)

            if copy:
                dest = self.target_dir / category / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest)

        return categories

    def build_dependency_map(self) -> Dict:
        """Return a dependency graph for all files in *source_dir*."""
        analysis = analyze_directory(str(self.source_dir))
        return analysis.get("dependency_graph", {})

    def generate_report(self, output_path: Optional[str] = None) -> Dict:
        """
        Run a full analysis of *source_dir* and generate an integration report.

        Args:
            output_path: Optional path to save the JSON report.

        Returns:
            Integration report dict.
        """
        analysis = analyze_directory(str(self.source_dir))
        arch_map = generate_architecture_map(analysis)
        categories = self.categorize_files(copy=False)

        report = {
            "source_dir": str(self.source_dir),
            "target_dir": str(self.target_dir),
            "total_files": analysis["total_files"],
            "language_distribution": analysis["language_distribution"],
            "categories": categories,
            "architecture_map": arch_map,
            "dependency_map": analysis.get("dependency_graph", {}),
        }

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2))

        return report

    def integrate(self, output_report_path: Optional[str] = None) -> Dict:
        """
        Copy files into categorised target directories and generate a report.

        Args:
            output_report_path: Optional path to save the JSON report.

        Returns:
            Integration report dict.
        """
        self.target_dir.mkdir(parents=True, exist_ok=True)
        categories = self.categorize_files(copy=True)

        analysis = analyze_directory(str(self.source_dir))
        arch_map = generate_architecture_map(analysis)

        report = {
            "status": "integrated",
            "source_dir": str(self.source_dir),
            "target_dir": str(self.target_dir),
            "total_files": analysis["total_files"],
            "language_distribution": analysis["language_distribution"],
            "categories": categories,
            "architecture_map": arch_map,
            "dependency_map": analysis.get("dependency_graph", {}),
        }

        if output_report_path:
            out = Path(output_report_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2))

        return report
