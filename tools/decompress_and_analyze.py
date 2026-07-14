#!/usr/bin/env python3
"""
CLI Tool: decompress_and_analyze.py
Extract a ZIP file, analyse its contents, and optionally integrate files into
categorised directories.

Usage:
    python tools/decompress_and_analyze.py <zip_file> [options]

Examples:
    # Extract and show a report
    python tools/decompress_and_analyze.py archive.zip --dest /tmp/extracted

    # Extract, categorise, and save reports
    python tools/decompress_and_analyze.py archive.zip \\
        --dest /tmp/extracted \\
        --integrate \\
        --report report.json

    # Just list the ZIP contents without extracting
    python tools/decompress_and_analyze.py archive.zip --list-only
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running from the repo root without installing as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.zip_extractor import ZipExtractor  # noqa: E402
from utils.file_analyzer import analyze_directory, generate_architecture_map, save_analysis_report  # noqa: E402
from utils.integration_manager import IntegrationManager  # noqa: E402


def _progress(extracted: int, total: int, current_file: str):
    if total == 0:
        return
    pct = int(extracted / total * 100)
    print(f"  [{pct:3d}%] ({extracted}/{total}) {current_file}", flush=True)


def cmd_list(args):
    """List ZIP contents without extracting."""
    print(f"Listing contents of: {args.zip_file}\n")
    manifest = ZipExtractor.list_contents(args.zip_file)
    print(f"Total entries       : {manifest['total_entries']}")
    print(f"Total compressed    : {manifest['total_compressed_bytes']:,} bytes")
    print(f"Total uncompressed  : {manifest['total_uncompressed_bytes']:,} bytes")
    print()
    for entry in manifest["entries"]:
        kind = "[DIR]" if entry["is_dir"] else "[FILE]"
        print(f"  {kind}  {entry['filename']}")


def cmd_extract(args):
    """Extract the ZIP and optionally analyse / integrate."""
    dest = args.dest or str(Path(args.zip_file).stem + "_extracted")
    print(f"Extracting: {args.zip_file} → {dest}")

    extractor = ZipExtractor(args.zip_file, dest)
    result = extractor.extract(
        progress_callback=_progress if not args.quiet else None
    )

    print("\nExtraction complete.")
    print(f"  Members : {result['total_members']}")
    print(f"  Extracted: {result['extracted']}")
    if result["errors"]:
        print(f"  Errors  : {len(result['errors'])}")
        for err in result["errors"]:
            print(f"    - {err['file']}: {err['error']}")

    # Analysis
    print(f"\nAnalysing extracted files in: {dest}")
    analysis = analyze_directory(dest)
    arch_map = generate_architecture_map(analysis)

    print(f"  Total files       : {analysis['total_files']}")
    print("  Language breakdown:")
    for lang, count in sorted(analysis["language_distribution"].items()):
        print(f"    {lang:20s}: {count}")
    if arch_map["entry_points"]:
        print(f"  Entry points      : {', '.join(arch_map['entry_points'])}")

    # Save analysis report
    if args.report:
        report_data = {
            "extraction": result,
            "analysis": analysis,
            "architecture_map": arch_map,
        }
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report_data, indent=2))
        print(f"\nReport saved to: {args.report}")

    # Integration
    if args.integrate:
        integrate_dir = args.integrate_dir or (str(Path(dest).parent / "integrated"))
        print(f"\nIntegrating files into categorised directories: {integrate_dir}")
        mgr = IntegrationManager(dest, integrate_dir)
        int_report = mgr.integrate(
            output_report_path=args.integration_report or None
        )
        print("  Categories created:")
        for cat, files in sorted(int_report["categories"].items()):
            print(f"    {cat:20s}: {len(files)} file(s)")
        if args.integration_report:
            print(f"\nIntegration report saved to: {args.integration_report}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract and analyse ZIP archives.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("zip_file", help="Path to the ZIP file.")
    parser.add_argument("--dest", help="Destination directory for extracted files.")
    parser.add_argument("--list-only", action="store_true",
                        help="List ZIP contents without extracting.")
    parser.add_argument("--report", metavar="PATH",
                        help="Save analysis report to this JSON file.")
    parser.add_argument("--integrate", action="store_true",
                        help="Organise extracted files by category.")
    parser.add_argument("--integrate-dir", metavar="PATH",
                        help="Directory for categorised files (default: <dest>/../integrated).")
    parser.add_argument("--integration-report", metavar="PATH",
                        help="Save integration report to this JSON file.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-file progress output.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_only:
            cmd_list(args)
        else:
            return cmd_extract(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
