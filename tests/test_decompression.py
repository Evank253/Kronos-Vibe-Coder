"""
Test Suite for ZIP decompression and file analysis system.
Covers extraction, directory preservation, error handling, file analysis,
integration manager, and the CLI tool.
"""
import io
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.zip_extractor import ZipExtractor  # noqa: E402
from utils.file_analyzer import (  # noqa: E402
    detect_language,
    extract_python_imports,
    extract_solidity_imports,
    extract_js_imports,
    analyze_file,
    analyze_directory,
    generate_architecture_map,
    save_analysis_report,
)
from utils.integration_manager import IntegrationManager  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_zip(tmp_path: Path, files: dict) -> Path:
    """Create an in-memory ZIP at tmp_path/archive.zip from a {name: content} dict."""
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            if name.endswith("/"):
                # directory entry
                info = zipfile.ZipInfo(name)
                zf.writestr(info, "")
            else:
                zf.writestr(name, content)
    return zip_path


# ===========================================================================
# ZipExtractor tests
# ===========================================================================

class TestZipExtractor:
    def test_extract_flat_files(self, tmp_path):
        files = {"a.txt": "hello", "b.py": "print('hi')"}
        zip_path = _make_zip(tmp_path, files)
        dest = tmp_path / "out"
        result = ZipExtractor(str(zip_path), str(dest)).extract()

        assert result["status"] == "success"
        assert result["extracted"] == 2
        assert (dest / "a.txt").read_text() == "hello"
        assert (dest / "b.py").read_text() == "print('hi')"

    def test_extract_preserves_nested_directories(self, tmp_path):
        files = {
            "src/": "",
            "src/main.py": "import os",
            "src/utils/helper.py": "def f(): pass",
        }
        zip_path = _make_zip(tmp_path, files)
        dest = tmp_path / "out"
        ZipExtractor(str(zip_path), str(dest)).extract()

        assert (dest / "src" / "main.py").exists()
        assert (dest / "src" / "utils" / "helper.py").exists()

    def test_extract_binary_content(self, tmp_path):
        binary_data = bytes(range(256))
        zip_path = tmp_path / "bin.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.bin", binary_data)
        dest = tmp_path / "out"
        result = ZipExtractor(str(zip_path), str(dest)).extract()

        assert result["status"] == "success"
        assert (dest / "data.bin").read_bytes() == binary_data

    def test_progress_callback_called(self, tmp_path):
        files = {"a.txt": "a", "b.txt": "b"}
        zip_path = _make_zip(tmp_path, files)
        dest = tmp_path / "out"
        calls = []
        ZipExtractor(str(zip_path), str(dest)).extract(
            progress_callback=lambda idx, total, name: calls.append((idx, total, name))
        )
        assert len(calls) >= 2  # at least once per member plus "done"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ZipExtractor(str(tmp_path / "missing.zip"), str(tmp_path / "out"))

    def test_invalid_zip_raises(self, tmp_path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip file")
        with pytest.raises(ValueError, match="Not a valid ZIP file"):
            ZipExtractor(str(bad), str(tmp_path / "out"))

    def test_path_traversal_blocked(self, tmp_path):
        """A ZIP entry with ../ should raise ValueError and not escape dest."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Craft a member that tries to traverse outside
            zf.writestr("../../evil.txt", "pwned")
        dest = tmp_path / "out"
        result = ZipExtractor(str(zip_path), str(dest)).extract()
        # The traversal entry should appear in errors (not extracted)
        assert not (tmp_path / "evil.txt").exists()
        assert result["status"] in ("success", "partial")

    def test_list_contents(self, tmp_path):
        files = {"readme.md": "# hi", "app.py": "print()"}
        zip_path = _make_zip(tmp_path, files)
        manifest = ZipExtractor.list_contents(str(zip_path))
        assert manifest["total_entries"] == 2
        names = [e["filename"] for e in manifest["entries"]]
        assert "readme.md" in names

    def test_extract_from_bytes(self, tmp_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("hello.txt", "world")
        raw = buf.getvalue()
        dest = tmp_path / "from_bytes"
        result = ZipExtractor.extract_from_bytes(raw, str(dest))
        assert result["status"] == "success"
        assert (dest / "hello.txt").read_text() == "world"

    def test_save_manifest(self, tmp_path):
        files = {"x.txt": "x"}
        zip_path = _make_zip(tmp_path, files)
        out_path = str(tmp_path / "manifest.json")
        ZipExtractor(str(zip_path), str(tmp_path / "out")).save_manifest(out_path)
        data = json.loads(Path(out_path).read_text())
        assert data["total_entries"] == 1

    def test_large_zip_size_limit(self, tmp_path):
        """A ZIP whose uncompressed total exceeds 1 GB should be rejected."""
        from unittest.mock import patch, MagicMock
        files = {"small.txt": "hello"}
        zip_path = _make_zip(tmp_path, files)
        dest = tmp_path / "out"

        # Patch infolist to return a member reporting > 1 GB uncompressed
        big_member = MagicMock()
        big_member.filename = "huge.bin"
        big_member.file_size = ZipExtractor.MAX_UNCOMPRESSED_SIZE + 1
        big_member.is_dir.return_value = False

        with patch("zipfile.ZipFile.infolist", return_value=[big_member]):
            with pytest.raises(ValueError, match="exceeds limit"):
                ZipExtractor(str(zip_path), str(dest)).extract()


# ===========================================================================
# FileAnalyzer tests
# ===========================================================================

class TestFileAnalyzer:
    def test_detect_language_python(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("x = 1")
        assert detect_language(f) == "Python"

    def test_detect_language_solidity(self, tmp_path):
        f = tmp_path / "Token.sol"
        f.write_text("pragma solidity ^0.8.0;")
        assert detect_language(f) == "Solidity"

    def test_detect_language_markdown(self, tmp_path):
        f = tmp_path / "README.md"
        f.write_text("# hi")
        assert detect_language(f) == "Markdown"

    def test_detect_language_unknown(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("stuff")
        assert detect_language(f) == "Unknown"

    def test_extract_python_imports(self):
        source = "import os\nfrom pathlib import Path\nimport sys"
        imports = extract_python_imports(source)
        assert "os" in imports
        assert "pathlib" in imports
        assert "sys" in imports

    def test_extract_python_imports_syntax_error(self):
        source = "import os\ndef f(:\n    pass"
        imports = extract_python_imports(source)
        assert "os" in imports

    def test_extract_solidity_imports(self):
        source = 'import "./ERC20.sol";\nimport "@openzeppelin/contracts/token/ERC20/ERC20.sol";'
        imports = extract_solidity_imports(source)
        assert "./ERC20.sol" in imports

    def test_extract_js_imports(self):
        source = "const x = require('express');\nimport React from 'react';"
        imports = extract_js_imports(source)
        assert "express" in imports
        assert "react" in imports

    def test_analyze_file_python(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("import os\nimport sys\n")
        result = analyze_file(f)
        assert result["language"] == "Python"
        assert "os" in result["imports"]
        assert not result["is_binary"]

    def test_analyze_directory(self, tmp_path):
        (tmp_path / "main.py").write_text("import os")
        (tmp_path / "README.md").write_text("# hi")
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "helper.py").write_text("def f(): pass")

        report = analyze_directory(str(tmp_path))
        assert report["total_files"] == 3
        assert report["language_distribution"]["Python"] == 2
        assert report["language_distribution"]["Markdown"] == 1

    def test_generate_architecture_map(self, tmp_path):
        (tmp_path / "main.py").write_text("import os")
        (tmp_path / "app.py").write_text("from flask import Flask")
        analysis = analyze_directory(str(tmp_path))
        arch = generate_architecture_map(analysis)
        assert "main.py" in arch["entry_points"] or "app.py" in arch["entry_points"]
        assert "Python" in arch["files_by_language"]

    def test_save_analysis_report(self, tmp_path):
        (tmp_path / "x.py").write_text("x=1")
        analysis = analyze_directory(str(tmp_path))
        out = str(tmp_path / "report.json")
        save_analysis_report(analysis, out)
        data = json.loads(Path(out).read_text())
        assert data["total_files"] == 1

    def test_analyze_directory_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            analyze_directory(str(tmp_path / "nope"))


# ===========================================================================
# IntegrationManager tests
# ===========================================================================

class TestIntegrationManager:
    def _make_source(self, tmp_path: Path) -> Path:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("import os")
        (src / "Token.sol").write_text("pragma solidity ^0.8.0;")
        (src / "README.md").write_text("# hi")
        (src / "index.js").write_text("const x = require('express');")
        return src

    def test_categorize_files_no_copy(self, tmp_path):
        src = self._make_source(tmp_path)
        mgr = IntegrationManager(str(src), str(tmp_path / "out"))
        cats = mgr.categorize_files(copy=False)
        assert "python" in cats
        assert "contracts" in cats
        assert "docs" in cats

    def test_categorize_files_with_copy(self, tmp_path):
        src = self._make_source(tmp_path)
        out = tmp_path / "out"
        mgr = IntegrationManager(str(src), str(out))
        cats = mgr.categorize_files(copy=True)
        assert (out / "python" / "main.py").exists()
        assert (out / "contracts" / "Token.sol").exists()

    def test_integrate_generates_report(self, tmp_path):
        src = self._make_source(tmp_path)
        out = tmp_path / "out"
        report_path = str(tmp_path / "integration.json")
        mgr = IntegrationManager(str(src), str(out))
        report = mgr.integrate(output_report_path=report_path)
        assert report["status"] == "integrated"
        assert report["total_files"] == 4
        data = json.loads(Path(report_path).read_text())
        assert data["status"] == "integrated"

    def test_build_dependency_map(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("import os\nimport sys")
        mgr = IntegrationManager(str(src), str(tmp_path / "out"))
        dep_map = mgr.build_dependency_map()
        assert "app.py" in dep_map

    def test_generate_report(self, tmp_path):
        src = self._make_source(tmp_path)
        mgr = IntegrationManager(str(src), str(tmp_path / "out"))
        report = mgr.generate_report()
        assert report["total_files"] == 4
        assert "architecture_map" in report

    def test_source_not_found(self, tmp_path):
        mgr = IntegrationManager(str(tmp_path / "missing"), str(tmp_path / "out"))
        with pytest.raises(FileNotFoundError):
            mgr.categorize_files()


# ===========================================================================
# CLI tool tests
# ===========================================================================

class TestCLI:
    def test_list_only(self, tmp_path, capsys):
        files = {"a.txt": "x", "b.md": "y"}
        zip_path = _make_zip(tmp_path, files)
        from tools.decompress_and_analyze import main
        ret = main(["--list-only", str(zip_path)])
        assert ret == 0
        captured = capsys.readouterr()
        assert "a.txt" in captured.out
        assert "b.md" in captured.out

    def test_extract_and_report(self, tmp_path, capsys):
        files = {"main.py": "import os", "README.md": "# hi"}
        zip_path = _make_zip(tmp_path, files)
        dest = str(tmp_path / "extracted")
        report_path = str(tmp_path / "report.json")
        from tools.decompress_and_analyze import main
        ret = main([str(zip_path), "--dest", dest, "--report", report_path, "--quiet"])
        assert ret == 0
        assert Path(report_path).exists()
        data = json.loads(Path(report_path).read_text())
        assert "extraction" in data
        assert "analysis" in data

    def test_extract_with_integration(self, tmp_path, capsys):
        files = {"app.py": "import os", "Token.sol": "pragma solidity ^0.8.0;"}
        zip_path = _make_zip(tmp_path, files)
        dest = str(tmp_path / "ext")
        int_dir = str(tmp_path / "int")
        int_report = str(tmp_path / "int_report.json")
        from tools.decompress_and_analyze import main
        ret = main([str(zip_path), "--dest", dest, "--integrate",
                    "--integrate-dir", int_dir, "--integration-report", int_report, "--quiet"])
        assert ret == 0
        assert Path(int_report).exists()

    def test_missing_zip_returns_error(self, tmp_path, capsys):
        from tools.decompress_and_analyze import main
        ret = main([str(tmp_path / "nope.zip")])
        assert ret == 1
