from pathlib import Path
import csv
import re
import shutil
import subprocess
import zipfile


# ============================================
# BUILD WORKFLOW CATALOG SEED FROM VIDEOS - V1
# ============================================
#
# PURPOSE
# -------
# Build workflow catalog seed rows from reference ZIP videos.
#
# This script follows the "mechanic" rule:
#
#   ZIP name / video name = known metadata
#   OCR text              = unit/model names only
#
# It does NOT:
#   - build resolver candidates
#   - score matches
#   - approve names
#   - merge into workflow_catalog.csv
#   - pretend OCR is truth
#
# It DOES:
#   - extract videos safely
#   - preserve original video filenames
#   - extract frames
#   - OCR visible model/unit names
#   - clean obvious UI junk
#   - remove known faction/subfaction prefixes from Unit
#   - write reviewable seed CSV files
#
# OUTPUT:
#
#   data/workflows/workflow_catalog/workflow_catalog_seed_from_videos_v1.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_ZIP_DIR = PROJECT_ROOT / "incoming" / "catalog_reference_zips"

WORK_DIR = PROJECT_ROOT / "data" / "workflows" / "catalog_reference_work"

FRAME_DIR = WORK_DIR / "frames"
TEXT_DIR = WORK_DIR / "ocr_text"

OUTPUT_DIR = PROJECT_ROOT / "data" / "workflows" / "workflow_catalog"

OUTPUT_FILE = OUTPUT_DIR / "workflow_catalog_seed_from_videos_v1.csv"

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ===============
# COMMAND HELPERS
# ===============

def run(command):
    result = subprocess.run(
        command,
        capture_output=True,
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if result.returncode != 0:
        if stderr.strip():
            print(stderr.strip())
        return ""

    return stdout


def safe_name(text):
    text = text.replace("'", "")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def make_workflow_id(superfaction, faction, subfaction, unit):
    text = "_".join(
        part for part in [
            superfaction,
            faction,
            subfaction,
            unit,
            "Workflow",
        ]
        if part
    )

    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


# ================
# METADATA PARSING
# ================

def infer_superfaction(zip_name):
    name = zip_name.lower()

    if "xenos" in name:
        return "Xenos"

    if "imperium" in name:
        return "Imperium"

    if "chaos" in name:
        return "Chaos"

    return ""


def normalize_video_title(video_name):
    title = Path(video_name).stem
    title = title.replace("_", " ")
    title = title.replace("--", " - ")
    title = title.replace("-", " - ")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def split_title_parts(video_name):
    title = normalize_video_title(video_name)

    parts = [
        part.strip()
        for part in title.split(" - ")
        if part.strip()
    ]

    return parts


def parse_video_metadata(zip_name, original_video_name):
    """
    Parse known metadata from the ZIP name and video filename.

    This is the important part.

    The video title tells us the faction/subfaction context.
    OCR should not be responsible for those fields.

    Example:
        ZIP: Imperium - Adeptus Astartes.zip
        Video: Raven Guard.MP4

    Output:
        Superfaction = Imperium
        Faction      = Adeptus Astartes
        Subfaction   = Raven Guard

    Example:
        ZIP: Xenos.zip
        Video: Drukhari Black Descent - Coven of Twelve - Cult of Red Grief.mp4

    Output rows will use:
        Superfaction = Xenos
        Faction      = Drukhari
        Subfaction   = Black Descent; Coven of Twelve; Cult of Red Grief
    """

    superfaction = infer_superfaction(zip_name)
    zip_lower = zip_name.lower()
    title = normalize_video_title(original_video_name)
    title_lower = title.lower()
    parts = split_title_parts(original_video_name)

    faction = ""
    subfactions = []

    # --------------------
    # Adeptus Astartes ZIP
    # --------------------

    if "adeptus astartes" in zip_lower:
        faction = "Adeptus Astartes"

        chapter_map = {
            "black templar": "Black Templars",
            "blood angels": "Blood Angels",
            "deathwatch": "Deathwatch",
            "grey knights": "Grey Knights",
            "imperial fists": "Imperial Fists",
            "iron hands": "Iron Hands",
            "raven guard": "Raven Guard",
            "salamanders": "Salamanders",
            "space wolves": "Space Wolves",
            "ultramarines": "Ultramarines",
            "white scar": "White Scars",
            "white scars": "White Scars",
        }

        for key, value in chapter_map.items():
            if key in title_lower:
                subfactions.append(value)

        # Cadian - Kasrkin is misplaced in this ZIP but the title tells the truth.
        if "cadian" in title_lower or "kasrkin" in title_lower or "karskin" in title_lower:
            faction = "Astra Militarum"
            subfactions = ["Cadian"]

        return {
            "Superfaction": superfaction,
            "Faction": faction,
            "Subfaction": "; ".join(subfactions),
            "Army": subfactions[0] if subfactions else faction,
        }

    # ------------------
    # Imperium mixed ZIP
    # ------------------

    if superfaction == "Imperium":
        if "adeptus custodes" in title_lower:
            faction = "Adeptus Custodes"
            subfactions = [p for p in parts[1:]]

        elif "adeptus sororitas" in title_lower:
            faction = "Adeptus Sororitas"
            subfactions = [p for p in parts[1:]]

        elif "astra militarum" in title_lower:
            faction = "Astra Militarum"
            first = parts[0].replace("Astra Militarum", "").strip()
            if first:
                subfactions.append(first)
            subfactions.extend(parts[1:])

        elif "agents of the imperium" in title_lower:
            faction = "Agents of the Imperium"
            first = parts[0].replace("Agents of the Imperium", "").strip()
            if first:
                subfactions.append(first)
            subfactions.extend(parts[1:])

        elif "adeptus mechanicus" in title_lower:
            faction = "Adeptus Mechanicus"

        else:
            faction = "Imperium"

        return {
            "Superfaction": superfaction,
            "Faction": faction,
            "Subfaction": "; ".join(subfactions),
            "Army": subfactions[0] if subfactions else faction,
        }

    # ----------
    # Xenox Zip
    # ----------

    if superfaction == "Xenos":
        first = parts[0] if parts else title
        first_lower = first.lower()

        xenos_faction_rules = [
            ("aeldari", "Aeldari"),
            ("drukhari", "Drukhari"),
            ("genestealer cults", "Genestealer Cults"),
            ("leagues of votann", "Leagues of Votann"),
            ("necrons", "Necrons"),
            ("orks", "Orks"),
            ("t'au empire", "T'au Empire"),
            ("tau empire", "T'au Empire"),
            ("tyranids", "Tyranids"),
        ]

        for key, value in xenos_faction_rules:
            if key in first_lower:
                faction = value
                break

        if not faction:
            faction = first

        first_clean = first

        for faction_name in [
            "Aeldari",
            "Drukhari",
            "Genestealer Cults",
            "Leagues of Votann",
            "Necrons",
            "Orks",
            "T'au Empire",
            "Tau Empire",
            "Tyranids",
        ]:
            first_clean = re.sub(
                re.escape(faction_name),
                "",
                first_clean,
                flags=re.IGNORECASE,
            ).strip()

        if first_clean:
            subfactions.append(first_clean)

        subfactions.extend(parts[1:])

        return {
            "Superfaction": superfaction,
            "Faction": faction,
            "Subfaction": "; ".join(subfactions),
            "Army": subfactions[0] if subfactions else faction,
        }

    # ---------------
    # Chaos fallback
    # ---------------

    if superfaction == "Chaos":
        first = parts[0] if parts else title

        chaos_rules = [
            ("world eaters", "World Eaters"),
            ("death guard", "Death Guard"),
            ("thousand sons", "Thousand Sons"),
            ("emperors children", "Emperor's Children"),
            ("emperor's children", "Emperor's Children"),
            ("black legion", "Black Legion"),
            ("word bearers", "Word Bearers"),
            ("iron warriors", "Iron Warriors"),
            ("night lords", "Night Lords"),
            ("alpha legion", "Alpha Legion"),
            ("chaos daemons", "Chaos Daemons"),
        ]

        sub = ""

        for key, value in chaos_rules:
            if key in title_lower:
                sub = value
                break

        return {
            "Superfaction": superfaction,
            "Faction": "Chaos Space Marines" if sub != "Chaos Daemons" else "Chaos Daemons",
            "Subfaction": sub,
            "Army": sub,
        }

    return {
        "Superfaction": superfaction,
        "Faction": "",
        "Subfaction": "",
        "Army": "",
    }


# =============
# UNIT CLEANING
# =============

def clean_unit_line(line):
    original = line
    line = line.strip()

    if not line:
        return ""

    lowered = line.lower()

    junk_patterns = [
        r"^\d+:\d+",
        r"search",
        r"cancel",
        r"filter",
        r"sort by",
        r"paint by model",
        r"home",
        r"paint$",
        r"learn",
        r"projects",
        r"profile",
        r"^\+$",
        r"^\|$",
        r"^-$",
        r"^.$",
    ]

    for pattern in junk_patterns:
        if re.search(pattern, lowered):
            return ""

    line = re.sub(r"[|•©®™]", "", line)
    line = re.sub(r"\s+", " ", line).strip()
    line = line.strip("+-_=~:;,. ")

    # Remove app count junk like:
    #   Raven Guard Intercessors (+)
    #   Raven Guard Incursors (+)
    line = line.replace("(+)", "").strip()
    line = line.replace("(+ ", "").strip()
    line = line.replace("+)", "").strip()

    # Remove leading OCR trash.
    line = re.sub(r"^[xz]\s+", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\d+\s+", "", line)

    if len(line) < 3:
        return ""

    if line.isdigit():
        return ""

    return line


def strip_metadata_from_unit(unit, metadata):
    """
    Remove faction/subfaction words from the Unit column.

    This is the exact fix you were pointing at.

    Example:
        Superfaction = Imperium
        Faction      = Adeptus Astartes
        Subfaction   = Raven Guard
        OCR Unit     = Raven Guard Intercessors

    Output:
        Intercessors

    We do NOT want the Unit column repeating metadata.
    """

    cleaned = unit.strip()

    removals = []

    for col in ["Superfaction", "Faction", "Army"]:
        value = metadata.get(col, "")
        if value:
            removals.append(value)

    subfaction_text = metadata.get("Subfaction", "")

    if subfaction_text:
        removals.extend(
            part.strip()
            for part in subfaction_text.split(";")
            if part.strip()
        )

    removals = sorted(removals, key=len, reverse=True)

    for value in removals:
        cleaned = re.sub(
            r"^" + re.escape(value) + r"\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip(" -_:;,. ")

    return cleaned if cleaned else unit.strip()


def infer_unit_type(unit):
    text = unit.lower()

    character_terms = [
        "captain",
        "lieutenant",
        "chaplain",
        "librarian",
        "ancient",
        "apothecary",
        "sergeant",
        "commander",
        "colonel",
        "lord",
        "prince",
        "champion",
        "shaan",
        "shrike",
        "harker",
        "straken",
        "marbo",
        "aun",
        "farsight",
        "shadowsun",
    ]

    vehicle_terms = [
        "rhino",
        "chimera",
        "tank",
        "dreadnought",
        "impulsor",
        "repulsor",
        "predator",
        "deathstrike",
        "speeder",
        "warsuit",
        "invictor",
    ]

    monster_terms = [
        "carnifex",
        "tyrant",
        "mawloc",
        "trygon",
        "haruspex",
        "psychophage",
        "screamer killer",
        "vortex beast",
    ]

    if any(term in text for term in character_terms):
        return "Character"

    if any(term in text for term in vehicle_terms):
        return "Vehicle"

    if any(term in text for term in monster_terms):
        return "Monster"

    return "Infantry"


# =================
# ZIP / VIDEO / OCR
# =================

def extract_zip(zip_path, destination):
    """
    Extract videos using short safe names but preserve original names
    in a mapping list.

    This avoids Windows path-length bullshit while still keeping the
    original video title for metadata.
    """

    destination.mkdir(parents=True, exist_ok=True)

    extracted = []

    with zipfile.ZipFile(zip_path, "r") as z:
        video_index = 0

        for info in z.infolist():
            if info.is_dir():
                continue

            original_name = Path(info.filename).name
            suffix = Path(original_name).suffix.lower()

            if suffix not in VIDEO_SUFFIXES:
                continue

            video_index += 1

            safe_video_name = f"video_{video_index:03d}{suffix}"
            target_path = destination / safe_video_name

            with z.open(info) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)

            extracted.append(
                {
                    "safe_path": target_path,
                    "original_name": original_name,
                }
            )

    return extracted


def video_duration(video_path):
    output = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
    )

    try:
        return float(output.strip())
    except Exception:
        return 0.0


def sample_times(duration):
    """
    Sample enough points to catch scrolling list screens without
    going insane.

    If this misses names, lower interval behavior later.
    For now this is a simple mechanic pass.
    """

    if duration <= 0:
        return []

    interval = 1.0

    times = []
    current = 0.5

    while current < duration:
        times.append(current)
        current += interval

    return times


def extract_frame(video_path, timestamp, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=900:-1",
            str(output_path),
        ],
        text=True,
    )


def ocr_image(image_path):
    return run(
        [
            TESSERACT_EXE,
            str(image_path),
            "stdout",
            "--psm",
            "6",
        ]
    )


def process_video(zip_name, safe_video_path, original_video_name):
    metadata = parse_video_metadata(
        zip_name=zip_name,
        original_video_name=original_video_name,
    )

    duration = video_duration(safe_video_path)
    times = sample_times(duration)

    records = []

    video_key = safe_name(Path(original_video_name).stem)

    if len(video_key) > 60:
        video_key = video_key[:60]

    video_key = f"{safe_name(Path(safe_video_path).stem)}_{video_key}"

    for index, timestamp in enumerate(times, start=1):
        frame_path = FRAME_DIR / video_key / f"frame_{index:04d}.png"

        extract_frame(
            video_path=safe_video_path,
            timestamp=timestamp,
            output_path=frame_path,
        )

        if not frame_path.exists():
            continue

        text = ocr_image(frame_path)

        text_file = TEXT_DIR / f"{video_key}_frame_{index:04d}.txt"
        text_file.parent.mkdir(parents=True, exist_ok=True)
        text_file.write_text(text, encoding="utf-8")

        for raw_line in text.splitlines():
            unit = clean_unit_line(raw_line)

            if not unit:
                continue

            unit = strip_metadata_from_unit(
                unit=unit,
                metadata=metadata,
            )

            if not unit:
                continue

            workflow_id = make_workflow_id(
                metadata["Superfaction"],
                metadata["Faction"],
                metadata["Subfaction"],
                unit,
            )

            records.append(
                {
                    "Workflow_ID": workflow_id,
                    "Superfaction": metadata["Superfaction"],
                    "Faction": metadata["Faction"],
                    "Subfaction": metadata["Subfaction"],
                    "Army": metadata["Army"],
                    "Unit": unit,
                    "Unit_Type": infer_unit_type(unit),
                    "Source": zip_name,
                    "Source_Video": original_video_name,
                    "Review_Status": "Needs Review",
                    "Notes": "Seeded from reference video OCR. Verify before merge.",
                }
            )

    return records


# ====
# MAIN
# ====

def main():
    print("=" * 5)
    print("BUILD WORKFLOW CATALOG SEED FROM VIDEOS V1")
    print("=" * 5)

    if not SOURCE_ZIP_DIR.exists():
        print()
        print("Missing folder:")
        print(SOURCE_ZIP_DIR)
        print()
        print("Put reference ZIPs here:")
        print(SOURCE_ZIP_DIR)
        return

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    zip_files = sorted(SOURCE_ZIP_DIR.glob("*.zip"))

    if not zip_files:
        print("No ZIP files found.")
        return

    all_records = []

    for zip_path in zip_files:
        print()
        print(f"ZIP: {zip_path.name}")

        extract_dir = WORK_DIR / "extracted" / safe_name(zip_path.stem)

        extracted_videos = extract_zip(
            zip_path=zip_path,
            destination=extract_dir,
        )

        print(f"Videos found: {len(extracted_videos)}")

        for item in extracted_videos:
            safe_path = item["safe_path"]
            original_name = item["original_name"]

            print(f"  Processing: {original_name}")

            records = process_video(
                zip_name=zip_path.name,
                safe_video_path=safe_path,
                original_video_name=original_name,
            )

            all_records.extend(records)

    if not all_records:
        print("No seed rows created.")
        return

    # Deduplicate exact workflow rows.
    unique = {}

    for record in all_records:
        key = (
            record["Workflow_ID"],
            record["Superfaction"],
            record["Faction"],
            record["Subfaction"],
            record["Unit"],
        )

        if key not in unique:
            unique[key] = record

    final_records = list(unique.values())

    final_records = sorted(
        final_records,
        key=lambda row: (
            row["Superfaction"],
            row["Faction"],
            row["Subfaction"],
            row["Unit"],
        ),
    )

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Workflow_ID",
                "Superfaction",
                "Faction",
                "Subfaction",
                "Army",
                "Unit",
                "Unit_Type",
                "Source",
                "Source_Video",
                "Review_Status",
                "Notes",
            ],
        )

        writer.writeheader()
        writer.writerows(final_records)

    print()
    print("SUMMARY")
    print("-" * 35)
    print(f"Raw rows ............ {len(all_records)}")
    print(f"Unique rows ......... {len(final_records)}")
    print()
    print("Written:")
    print(OUTPUT_FILE)

    print()
    print("Cleaning temporary catalog reference work folder...")

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    print("Temporary files removed.")

    print()
    print("=" * 41)
    print("CATALOG SEED BUILD COMPLETE")
    print("=" * 41)


if __name__ == "__main__":
    main()