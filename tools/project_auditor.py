#!/usr/bin/env python3
"""
AI Miniature Painting Assistant - Project Auditor

Run from the project root:

    python tools/project_auditor.py

Or run a full audit directly:

    python tools/project_auditor.py --full

Reports are written to:

    reports/project_audit/
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "cleanup_logs",
}

LEGACY_NAME_TERMS = {
    "ocr",
    "video",
    "frame",
    "scanner",
    "acquisition",
    "workflow_extractor",
    "workflow_csv_writer",
    "resolver",
    "review_queue",
    "deduplicator",
    "image_processing_log",
    "video_processing_log",
    "import_manager",
}

RUNTIME_ROOTS = {
    "main.py",
    "src",
    "database",
    "data",
}

REPORT_DIR = Path("reports") / "project_audit"


@dataclass(frozen=True)
class FileRecord:
    path: Path
    size: int
    suffix: str
    modified: float


def format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024

    return f"{size} B"


def normalized_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_exclude(path: Path, root: Path, excluded_dirs: set[str]) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    return any(part in excluded_dirs for part in relative.parts)


def scan_files(root: Path, excluded_dirs: set[str]) -> list[FileRecord]:
    records: list[FileRecord] = []

    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)

        dir_names[:] = [
            name
            for name in dir_names
            if name not in excluded_dirs
            and not should_exclude(current_path / name, root, excluded_dirs)
        ]

        for file_name in file_names:
            path = current_path / file_name

            if should_exclude(path, root, excluded_dirs):
                continue

            try:
                stat = path.stat()
            except OSError:
                continue

            records.append(
                FileRecord(
                    path=path,
                    size=stat.st_size,
                    suffix=path.suffix.lower(),
                    modified=stat.st_mtime,
                )
            )

    return records


def collect_directories(root: Path, excluded_dirs: set[str]) -> list[Path]:
    directories: list[Path] = []

    for current_root, dir_names, _ in os.walk(root):
        current_path = Path(current_root)

        dir_names[:] = [
            name
            for name in dir_names
            if name not in excluded_dirs
            and not should_exclude(current_path / name, root, excluded_dirs)
        ]

        for directory_name in dir_names:
            directories.append(current_path / directory_name)

    return directories


def calculate_top_level_sizes(
    root: Path,
    records: Iterable[FileRecord],
) -> dict[str, int]:
    sizes: dict[str, int] = defaultdict(int)

    for record in records:
        relative = record.path.relative_to(root)
        key = relative.parts[0] if relative.parts else record.path.name
        sizes[key] += record.size

    return dict(sorted(sizes.items(), key=lambda item: item[1], reverse=True))


def find_empty_directories(
    root: Path,
    directories: Iterable[Path],
    excluded_dirs: set[str],
) -> list[Path]:
    empty: list[Path] = []

    for directory in directories:
        try:
            visible_children = [
                child
                for child in directory.iterdir()
                if child.name not in excluded_dirs
            ]
        except OSError:
            continue

        if not visible_children:
            empty.append(directory)

    return sorted(empty, key=lambda path: normalized_relative(path, root))


def find_duplicate_filenames(records: Iterable[FileRecord]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)

    for record in records:
        grouped[record.path.name.lower()].append(record.path)

    return {
        name: sorted(paths)
        for name, paths in grouped.items()
        if len(paths) > 1
    }


def file_hash(path: Path, block_size: int = 1024 * 1024) -> str | None:
    digest = hashlib.sha256()

    try:
        with path.open("rb") as file_handle:
            while True:
                block = file_handle.read(block_size)
                if not block:
                    break
                digest.update(block)
    except OSError:
        return None

    return digest.hexdigest()


def find_duplicate_content(
    records: Iterable[FileRecord],
    max_file_size: int = 100 * 1024 * 1024,
) -> dict[str, list[Path]]:
    by_size: dict[int, list[Path]] = defaultdict(list)

    for record in records:
        if 0 < record.size <= max_file_size:
            by_size[record.size].append(record.path)

    duplicate_groups: dict[str, list[Path]] = {}

    for paths in by_size.values():
        if len(paths) < 2:
            continue

        by_hash: dict[str, list[Path]] = defaultdict(list)

        for path in paths:
            digest = file_hash(path)
            if digest:
                by_hash[digest].append(path)

        for digest, matching_paths in by_hash.items():
            if len(matching_paths) > 1:
                duplicate_groups[digest] = sorted(matching_paths)

    return duplicate_groups


def module_name_from_path(path: Path, root: Path) -> str | None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None

    if relative.suffix != ".py":
        return None

    parts = list(relative.with_suffix("").parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]

    if not parts:
        return None

    return ".".join(parts)


def parse_imports(path: Path) -> set[str]:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return set()

    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def build_python_import_graph(
    root: Path,
    records: Iterable[FileRecord],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, Path],
]:
    python_records = [record for record in records if record.suffix == ".py"]

    module_to_path: dict[str, Path] = {}
    path_to_module: dict[Path, str] = {}

    for record in python_records:
        module_name = module_name_from_path(record.path, root)

        if module_name:
            module_to_path[module_name] = record.path
            path_to_module[record.path] = module_name

    imports_by_module: dict[str, set[str]] = defaultdict(set)
    imported_by_module: dict[str, set[str]] = defaultdict(set)

    known_modules = set(module_to_path)

    for path, module_name in path_to_module.items():
        imports = parse_imports(path)

        for imported_name in imports:
            matched_module = None

            if imported_name in known_modules:
                matched_module = imported_name
            else:
                candidates = [
                    known
                    for known in known_modules
                    if imported_name.startswith(f"{known}.")
                    or known.startswith(f"{imported_name}.")
                ]

                if candidates:
                    matched_module = sorted(candidates, key=len, reverse=True)[0]

            if matched_module:
                imports_by_module[module_name].add(matched_module)
                imported_by_module[matched_module].add(module_name)

    return imports_by_module, imported_by_module, module_to_path


def find_legacy_candidates(
    root: Path,
    records: Iterable[FileRecord],
) -> list[Path]:
    candidates: list[Path] = []

    for record in records:
        relative = normalized_relative(record.path, root).lower()

        if relative.startswith("legacy/"):
            continue

        filename = record.path.name.lower()
        stem = record.path.stem.lower()

        if any(term in filename or term in stem for term in LEGACY_NAME_TERMS):
            candidates.append(record.path)

    return sorted(candidates, key=lambda path: normalized_relative(path, root))


def gitignore_audit(root: Path) -> list[str]:
    gitignore_path = root / ".gitignore"
    findings: list[str] = []

    if not gitignore_path.exists():
        return ["Missing .gitignore"]

    text = gitignore_path.read_text(encoding="utf-8", errors="replace")

    recommended = {
        ".venv/": "Virtual environment is not ignored",
        "__pycache__/": "Python cache directories are not ignored",
        "*.py[cod]": "Compiled Python files are not ignored",
        ".idea/": "PyCharm settings are not ignored",
        "project_tree*.txt": "Generated tree files are not ignored",
        "*.log": "Log files are not ignored",
        "~$*.xlsx": "Temporary Excel files are not ignored",
    }

    for pattern, message in recommended.items():
        if pattern not in text:
            findings.append(f"{message}: add `{pattern}`")

    suspicious_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().lower() in {"tatus --short", "git status --short"}
    ]

    for line in suspicious_lines:
        findings.append(f"Suspicious accidental line in .gitignore: `{line}`")

    return findings


def potential_dead_python_files(
    root: Path,
    imported_by_module: dict[str, set[str]],
    module_to_path: dict[str, Path],
) -> list[Path]:
    dead_candidates: list[Path] = []

    exempt_names = {
        "main",
        "__main__",
    }

    exempt_prefixes = (
        "tools.",
        "tests.",
        "legacy.",
    )

    for module, path in module_to_path.items():
        if module in exempt_names:
            continue

        if module.startswith(exempt_prefixes):
            continue

        if path.name == "__init__.py":
            continue

        if module not in imported_by_module:
            relative = normalized_relative(path, root)

            if relative.startswith("src/"):
                dead_candidates.append(path)

    return sorted(dead_candidates, key=lambda path: normalized_relative(path, root))


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None found._\n"

    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for row in rows:
        escaped = [cell.replace("|", r"\|") for cell in row]
        output.append("| " + " | ".join(escaped) + " |")

    return "\n".join(output) + "\n"


def generate_report(root: Path, include_content_duplicates: bool = False) -> Path:
    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
    records = scan_files(root, excluded_dirs)
    directories = collect_directories(root, excluded_dirs)

    extension_counts = Counter(
        record.suffix if record.suffix else "[no extension]"
        for record in records
    )

    top_level_sizes = calculate_top_level_sizes(root, records)
    empty_directories = find_empty_directories(root, directories, excluded_dirs)
    duplicate_names = find_duplicate_filenames(records)
    duplicate_content = (
        find_duplicate_content(records)
        if include_content_duplicates
        else {}
    )

    imports_by_module, imported_by_module, module_to_path = (
        build_python_import_graph(root, records)
    )

    legacy_candidates = find_legacy_candidates(root, records)
    dead_candidates = potential_dead_python_files(
        root,
        imported_by_module,
        module_to_path,
    )
    ignore_findings = gitignore_audit(root)

    largest_files = sorted(
        records,
        key=lambda record: record.size,
        reverse=True,
    )[:50]

    total_size = sum(record.size for record in records)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_directory = root / REPORT_DIR
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / "project_audit.md"

    lines: list[str] = [
        "# AI Miniature Painting Assistant — Project Audit",
        "",
        f"Generated: `{timestamp}`",
        f"Root: `{root}`",
        "",
        "## Summary",
        "",
        markdown_table(
            ["Metric", "Value"],
            [
                ["Total files", f"{len(records):,}"],
                ["Total directories", f"{len(directories):,}"],
                ["Total size", format_size(total_size)],
                ["Python files", f"{extension_counts.get('.py', 0):,}"],
                ["CSV files", f"{extension_counts.get('.csv', 0):,}"],
                ["XLSX files", f"{extension_counts.get('.xlsx', 0):,}"],
                ["SQLite/DB files", f"{extension_counts.get('.db', 0) + extension_counts.get('.sqlite', 0) + extension_counts.get('.sqlite3', 0):,}"],
                ["Empty directories", f"{len(empty_directories):,}"],
                ["Duplicate filenames", f"{len(duplicate_names):,}"],
                ["Legacy candidates", f"{len(legacy_candidates):,}"],
                ["Potential unreferenced runtime modules", f"{len(dead_candidates):,}"],
            ],
        ),
        "## Top-Level Folder Sizes",
        "",
        markdown_table(
            ["Folder/File", "Size"],
            [
                [name, format_size(size)]
                for name, size in top_level_sizes.items()
            ],
        ),
        "## File Types",
        "",
        markdown_table(
            ["Extension", "Count"],
            [
                [extension, f"{count:,}"]
                for extension, count in extension_counts.most_common()
            ],
        ),
        "## Largest Files",
        "",
        markdown_table(
            ["Path", "Size", "Modified"],
            [
                [
                    normalized_relative(record.path, root),
                    format_size(record.size),
                    datetime.fromtimestamp(record.modified).strftime("%Y-%m-%d %H:%M"),
                ]
                for record in largest_files
            ],
        ),
        "## Empty Directories",
        "",
    ]

    if empty_directories:
        lines.extend(
            f"- `{normalized_relative(path, root)}`"
            for path in empty_directories
        )
        lines.append("")
    else:
        lines.extend(["_None found._", ""])

    lines.extend(
        [
            "## Duplicate Filenames",
            "",
        ]
    )

    if duplicate_names:
        for name, paths in sorted(duplicate_names.items()):
            lines.append(f"### `{name}`")
            lines.append("")
            lines.extend(
                f"- `{normalized_relative(path, root)}`"
                for path in paths
            )
            lines.append("")
    else:
        lines.extend(["_None found._", ""])

    if include_content_duplicates:
        lines.extend(
            [
                "## Duplicate File Contents",
                "",
            ]
        )

        if duplicate_content:
            for digest, paths in duplicate_content.items():
                lines.append(f"### SHA-256 `{digest[:16]}...`")
                lines.append("")
                lines.extend(
                    f"- `{normalized_relative(path, root)}`"
                    for path in paths
                )
                lines.append("")
        else:
            lines.extend(["_None found._", ""])

    lines.extend(
        [
            "## Legacy Candidates",
            "",
            "These are filename-based candidates only. Review before moving or deleting.",
            "",
        ]
    )

    if legacy_candidates:
        lines.extend(
            f"- `{normalized_relative(path, root)}`"
            for path in legacy_candidates
        )
        lines.append("")
    else:
        lines.extend(["_None found._", ""])

    lines.extend(
        [
            "## Potential Unreferenced Runtime Modules",
            "",
            "These are Python files under `src/` that no other scanned project module imports. "
            "They may still be entry points, dynamically loaded, or used externally.",
            "",
        ]
    )

    if dead_candidates:
        lines.extend(
            f"- `{normalized_relative(path, root)}`"
            for path in dead_candidates
        )
        lines.append("")
    else:
        lines.extend(["_None found._", ""])

    lines.extend(
        [
            "## Python Import Relationships",
            "",
        ]
    )

    import_rows: list[list[str]] = []

    for module in sorted(module_to_path):
        imports = sorted(imports_by_module.get(module, set()))
        imported_by = sorted(imported_by_module.get(module, set()))

        import_rows.append(
            [
                module,
                ", ".join(imports[:8]) + ("…" if len(imports) > 8 else ""),
                ", ".join(imported_by[:8]) + ("…" if len(imported_by) > 8 else ""),
            ]
        )

    lines.append(
        markdown_table(
            ["Module", "Imports Project Modules", "Imported By"],
            import_rows,
        )
    )

    lines.extend(
        [
            "## .gitignore Audit",
            "",
        ]
    )

    if ignore_findings:
        lines.extend(f"- {finding}" for finding in ignore_findings)
        lines.append("")
    else:
        lines.extend(["_No obvious issues found._", ""])

    lines.extend(
        [
            "## Cleanup Guidance",
            "",
            "1. Remove genuinely empty folders.",
            "2. Review legacy candidates that remain outside `legacy/`.",
            "3. Review duplicate filenames before consolidating anything.",
            "4. Treat unreferenced modules as review candidates, not automatic deletions.",
            "5. Run the application and tests after every move batch.",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def print_quick_stats(root: Path) -> None:
    records = scan_files(root, set(DEFAULT_EXCLUDED_DIRS))
    total_size = sum(record.size for record in records)
    suffix_counts = Counter(record.suffix or "[no extension]" for record in records)

    print()
    print("=" * 60)
    print("PROJECT STATISTICS")
    print("=" * 60)
    print(f"Files:         {len(records):,}")
    print(f"Total size:    {format_size(total_size)}")
    print(f"Python:        {suffix_counts.get('.py', 0):,}")
    print(f"CSV:           {suffix_counts.get('.csv', 0):,}")
    print(f"XLSX:          {suffix_counts.get('.xlsx', 0):,}")
    print(f"Markdown:      {suffix_counts.get('.md', 0):,}")
    print()


def print_folder_sizes(root: Path) -> None:
    records = scan_files(root, set(DEFAULT_EXCLUDED_DIRS))
    sizes = calculate_top_level_sizes(root, records)

    print()
    print("=" * 60)
    print("TOP-LEVEL SIZES")
    print("=" * 60)

    for name, size in sizes.items():
        print(f"{name:<40} {format_size(size):>15}")

    print()


def print_largest_files(root: Path, count: int = 30) -> None:
    records = scan_files(root, set(DEFAULT_EXCLUDED_DIRS))
    largest = sorted(records, key=lambda record: record.size, reverse=True)[:count]

    print()
    print("=" * 60)
    print("LARGEST FILES")
    print("=" * 60)

    for record in largest:
        relative = normalized_relative(record.path, root)
        print(f"{format_size(record.size):>12}  {relative}")

    print()


def print_empty_directories(root: Path) -> None:
    excluded = set(DEFAULT_EXCLUDED_DIRS)
    directories = collect_directories(root, excluded)
    empty = find_empty_directories(root, directories, excluded)

    print()
    print("=" * 60)
    print("EMPTY DIRECTORIES")
    print("=" * 60)

    if not empty:
        print("None found.")
    else:
        for path in empty:
            print(normalized_relative(path, root))

    print()


def print_menu() -> None:
    print("=" * 60)
    print("AI MINIATURE PAINTING ASSISTANT - PROJECT AUDITOR")
    print("=" * 60)
    print("[1] Project statistics")
    print("[2] Top-level folder sizes")
    print("[3] Largest files")
    print("[4] Empty folders")
    print("[5] Generate full audit report")
    print("[6] Generate full audit with duplicate-content hashing")
    print("[Q] Quit")
    print()


def interactive_menu(root: Path) -> None:
    while True:
        print_menu()
        choice = input("Select an option: ").strip().lower()

        if choice == "1":
            print_quick_stats(root)
        elif choice == "2":
            print_folder_sizes(root)
        elif choice == "3":
            print_largest_files(root)
        elif choice == "4":
            print_empty_directories(root)
        elif choice == "5":
            report = generate_report(root, include_content_duplicates=False)
            print(f"\nAudit written to:\n{report}\n")
        elif choice == "6":
            print("\nHashing duplicate-content candidates. This may take longer.")
            report = generate_report(root, include_content_duplicates=True)
            print(f"\nAudit written to:\n{report}\n")
        elif choice in {"q", "quit", "exit"}:
            return
        else:
            print("\nInvalid selection.\n")


def resolve_project_root(explicit_root: str | None) -> Path:
    if explicit_root:
        root = Path(explicit_root).expanduser().resolve()
    else:
        root = Path.cwd().resolve()

    missing = [
        item
        for item in RUNTIME_ROOTS
        if not (root / item).exists()
    ]

    if missing:
        print(
            "Warning: this may not be the project root. Missing: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )

    return root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the AI Miniature Painting Assistant project."
    )
    parser.add_argument(
        "--root",
        help="Project root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate a full audit report without opening the menu.",
    )
    parser.add_argument(
        "--hash-duplicates",
        action="store_true",
        help="Hash same-sized files to detect duplicate contents.",
    )

    args = parser.parse_args()
    root = resolve_project_root(args.root)

    if args.full:
        report = generate_report(
            root,
            include_content_duplicates=args.hash_duplicates,
        )
        print(f"Audit written to: {report}")
        return 0

    interactive_menu(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
