"""
ZIP Decompression Module
Extracts ZIP files with full path preservation, metadata, and progress tracking.
"""
import io
import json
import os
import stat
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional


class ZipExtractor:
    """Extract ZIP archives with structure preservation and progress tracking."""

    # Maximum allowed uncompressed size (1 GB)
    MAX_UNCOMPRESSED_SIZE = 1024 * 1024 * 1024

    def __init__(self, zip_path: str, dest_dir: str):
        self.zip_path = Path(zip_path)
        self.dest_dir = Path(dest_dir)
        self._validate_zip()

    def _validate_zip(self):
        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {self.zip_path}")
        if not zipfile.is_zipfile(self.zip_path):
            raise ValueError(f"Not a valid ZIP file: {self.zip_path}")

    def _safe_path(self, member_name: str) -> Path:
        """Prevent path traversal attacks by resolving member path safely."""
        dest = self.dest_dir.resolve()
        target = (dest / member_name).resolve()
        if not str(target).startswith(str(dest)):
            raise ValueError(
                f"Path traversal detected in ZIP: {member_name!r} would escape "
                f"destination {dest}"
            )
        return target

    def extract(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        password: Optional[bytes] = None,
    ) -> Dict:
        """
        Extract all files from the ZIP archive.

        Args:
            progress_callback: Optional callable(extracted_count, total_count, current_file)
            password: Optional ZIP password as bytes.

        Returns:
            Dict with extraction summary.
        """
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        extracted_files: List[Dict] = []
        errors: List[Dict] = []

        with zipfile.ZipFile(self.zip_path, "r") as zf:
            if password:
                zf.setpassword(password)

            members = zf.infolist()
            total = len(members)
            total_uncompressed = sum(m.file_size for m in members)

            if total_uncompressed > self.MAX_UNCOMPRESSED_SIZE:
                raise ValueError(
                    f"ZIP uncompressed size ({total_uncompressed} bytes) exceeds "
                    f"limit of {self.MAX_UNCOMPRESSED_SIZE} bytes (1 GB)."
                )

            for idx, member in enumerate(members):
                if progress_callback:
                    progress_callback(idx, total, member.filename)

                try:
                    target = self._safe_path(member.filename)

                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        data = zf.read(member.filename)
                        target.write_bytes(data)
                        self._restore_permissions(target, member)

                    extracted_files.append({
                        "path": str(target.relative_to(self.dest_dir)),
                        "is_dir": member.is_dir(),
                        "size": member.file_size,
                        "compress_type": member.compress_type,
                    })
                except Exception as exc:
                    errors.append({"file": member.filename, "error": str(exc)})

        if progress_callback:
            progress_callback(total, total, "done")

        return {
            "status": "success" if not errors else "partial",
            "zip_file": str(self.zip_path),
            "dest_dir": str(self.dest_dir),
            "total_members": total,
            "extracted": len(extracted_files),
            "errors": errors,
            "files": extracted_files,
        }

    @staticmethod
    def _restore_permissions(target: Path, member: zipfile.ZipInfo):
        """Restore Unix file permissions stored in the ZIP entry."""
        unix_mode = member.external_attr >> 16
        if unix_mode:
            # Only apply readable bits; ensure owner always has rw
            safe_mode = unix_mode & 0o777
            safe_mode |= stat.S_IRUSR | stat.S_IWUSR
            try:
                os.chmod(target, safe_mode)
            except OSError:
                pass

    @classmethod
    def list_contents(cls, zip_path: str) -> Dict:
        """Return a manifest of all entries in the ZIP without extracting."""
        path = Path(zip_path)
        if not path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        if not zipfile.is_zipfile(path):
            raise ValueError(f"Not a valid ZIP file: {zip_path}")

        entries = []
        with zipfile.ZipFile(path, "r") as zf:
            for member in zf.infolist():
                entries.append({
                    "filename": member.filename,
                    "is_dir": member.is_dir(),
                    "file_size": member.file_size,
                    "compress_size": member.compress_size,
                    "date_time": member.date_time,
                    "compress_type": member.compress_type,
                })

        total_compressed = sum(e["compress_size"] for e in entries)
        total_uncompressed = sum(e["file_size"] for e in entries)

        return {
            "zip_file": str(path),
            "total_entries": len(entries),
            "total_compressed_bytes": total_compressed,
            "total_uncompressed_bytes": total_uncompressed,
            "entries": entries,
        }

    @classmethod
    def extract_from_bytes(cls, zip_bytes: bytes, dest_dir: str) -> Dict:
        """
        Extract a ZIP supplied as raw bytes (e.g. from a file upload).

        Args:
            zip_bytes: Raw ZIP file bytes.
            dest_dir: Destination directory path.

        Returns:
            Dict with extraction summary.
        """
        buf = io.BytesIO(zip_bytes)
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        extracted_files = []
        errors = []

        with zipfile.ZipFile(buf, "r") as zf:
            members = zf.infolist()
            total_uncompressed = sum(m.file_size for m in members)

            if total_uncompressed > cls.MAX_UNCOMPRESSED_SIZE:
                raise ValueError(
                    f"ZIP uncompressed size ({total_uncompressed} bytes) exceeds "
                    f"limit of {cls.MAX_UNCOMPRESSED_SIZE} bytes (1 GB)."
                )

            for member in members:
                try:
                    dest_resolved = dest.resolve()
                    target = (dest_resolved / member.filename).resolve()
                    if not str(target).startswith(str(dest_resolved)):
                        raise ValueError(
                            f"Path traversal detected in ZIP: {member.filename!r} would escape "
                            f"destination {dest_resolved}"
                        )

                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(zf.read(member.filename))
                        cls._restore_permissions(target, member)

                    extracted_files.append({
                        "path": str(target.relative_to(dest)),
                        "is_dir": member.is_dir(),
                        "size": member.file_size,
                    })
                except Exception as exc:
                    errors.append({"file": member.filename, "error": str(exc)})

        return {
            "status": "success" if not errors else "partial",
            "dest_dir": str(dest),
            "total_members": len(members),
            "extracted": len(extracted_files),
            "errors": errors,
            "files": extracted_files,
        }

    def save_manifest(self, output_path: str) -> str:
        """Save the ZIP contents manifest to a JSON file."""
        manifest = self.list_contents(str(self.zip_path))
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2))
        return str(out)
