from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from src.core.paths import (
    REGISTRY_MANIFEST,
    REGISTRIES_CSV_DIR,
    REGISTRIES_XLSX_DIR,
    CSV_ARCHIVE_DIR,
    XLSX_ARCHIVE_DIR,
)

COMPANY_SLUGS = {
    "AK Interactive": "AK_Interactive",
    "Army Painter": "Army_Painter",
    "Games Workshop": "Games_Workshop",
    "Monument Hobbies": "Monument_Hobbies",
    "Vallejo": "Vallejo",
}


def load_manifest() -> dict:
    if not REGISTRY_MANIFEST.exists():
        return {}
    return json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    REGISTRY_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_MANIFEST.write_text(json.dumps(manifest, indent=4), encoding="utf-8")


def parse_version(value: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def format_version(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def bump_patch(version: str) -> str:
    major, minor, patch = parse_version(version)
    return format_version((major, minor, patch + 1))


def company_slug(company: str) -> str:
    return COMPANY_SLUGS.get(company, re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_"))


def registry_filename(company: str, version: str, suffix: str) -> str:
    if not suffix.startswith("."):
        suffix = "." + suffix
    return f"{company_slug(company)}_registry_{version}{suffix}"


def get_active_registry(company: str, file_type: str = "csv") -> Path:
    manifest = load_manifest()
    company_data = manifest.get(company)
    if not company_data:
        raise KeyError(f"No manifest entry for company: {company}")

    if file_type.lower() == "csv":
        filename = company_data.get("active_csv")
        folder = REGISTRIES_CSV_DIR
    elif file_type.lower() == "xlsx":
        filename = company_data.get("active_xlsx")
        folder = REGISTRIES_XLSX_DIR
    else:
        raise ValueError("file_type must be 'csv' or 'xlsx'")

    if not filename:
        raise KeyError(f"No active_{file_type} set for {company}")

    path = folder / filename
    if not path.exists():
        raise FileNotFoundError(f"Manifest points to missing file: {path}")

    return path


def get_active_version(company: str) -> str:
    manifest = load_manifest()
    company_data = manifest.get(company)
    if not company_data:
        raise KeyError(f"No manifest entry for company: {company}")
    return company_data.get("version", "0.0.0")


def get_next_version(company: str) -> str:
    return bump_patch(get_active_version(company))


def make_output_paths(company: str, version: str | None = None) -> tuple[Path, Path]:
    if version is None:
        version = get_next_version(company)
    csv_path = REGISTRIES_CSV_DIR / registry_filename(company, version, "csv")
    xlsx_path = REGISTRIES_XLSX_DIR / registry_filename(company, version, "xlsx")
    return csv_path, xlsx_path


def archive_file(path: Path) -> Path:
    if not path.exists():
        return path

    archive_dir = CSV_ARCHIVE_DIR if path.suffix.lower() == ".csv" else XLSX_ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / path.name

    if target.exists():
        counter = 1
        while target.exists():
            target = archive_dir / f"{path.stem}_archived_{counter}{path.suffix}"
            counter += 1

    shutil.move(str(path), str(target))
    return target


def set_active_registry(company: str, csv_path: Path, xlsx_path: Path | None = None, archive_previous: bool = True) -> None:
    manifest = load_manifest()
    company_data = manifest.setdefault(company, {})

    old_csv = company_data.get("active_csv")
    old_xlsx = company_data.get("active_xlsx")

    if archive_previous and old_csv:
        old_csv_path = REGISTRIES_CSV_DIR / old_csv
        if old_csv_path.exists() and old_csv_path.resolve() != csv_path.resolve():
            archive_file(old_csv_path)

    if archive_previous and old_xlsx and xlsx_path is not None:
        old_xlsx_path = REGISTRIES_XLSX_DIR / old_xlsx
        if old_xlsx_path.exists() and old_xlsx_path.resolve() != xlsx_path.resolve():
            archive_file(old_xlsx_path)

    version = format_version(parse_version(csv_path.name))
    company_data["version"] = version
    company_data["active_csv"] = csv_path.name
    if xlsx_path is not None:
        company_data["active_xlsx"] = xlsx_path.name

    save_manifest(manifest)
