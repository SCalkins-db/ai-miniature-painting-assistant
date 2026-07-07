from pathlib import Path
import csv
import re
import shutil
import subprocess
import zipfile


# ============================================================
# BUILD VERIFIED CATALOG CANDIDATES FROM VIDEOS - V1
# ============================================================
#
# PURPOSE
# -------
# Extract candidate unit / character / model names from the actual
# Warhammer app videos/screenshots.
#
# This does NOT create final trusted catalog rows.
# This creates a REVIEW FILE.
#
# Why?
# Because OCR sucks, but the video/app list is still the closest
# source to the real names.
#
# Correct flow:
#
#   ZIP videos
#       ↓
#   sample frames
#       ↓
#   OCR visible list names
#       ↓
#   candidate CSV
#       ↓
#   human approval
#       ↓
#   verified catalog
#
# DO NOT auto-merge this into workflow_catalog.csv.
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_ZIP_DIR = PROJECT_ROOT / "incoming" / "catalog_reference_zips"

WORK_DIR = PROJECT_ROOT / "data" / "workflows" / "catalog_reference_work"

FRAME_DIR = WORK_DIR / "frames"
TEXT_DIR = WORK_DIR / "ocr_text"

OUTPUT_DIR = PROJECT_ROOT / "data" / "workflows" / "workflow_catalog"

CANDIDATE_OUTPUT = OUTPUT_DIR / "workflow_catalog_candidates_from_videos_v1.csv"
UNIQUE_OUTPUT = OUTPUT_DIR / "workflow_catalog_unique_name_candidates_v1.csv"

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


def run(command):
    result = subprocess.run(
        command,
        capture_output=True,
    )

    stdout = result.stdout.decode(
        "utf-8",
        errors="replace",
    )

    stderr = result.stderr.decode(
        "utf-8",
        errors="replace",
    )

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


def clean_candidate_line(line):
    line = line.strip()

    junk_patterns = [
        r"^\d+:\d+",
        r"search",
        r"cancel",
        r"filter",
        r"sort by",
        r"paint by model",
        r"home",
        r"paint",
        r"learn",
        r"projects",
        r"profile",
        r"^\+$",
        r"^\|$",
        r"^-$",
        r"^.$",
    ]

    lowered = line.lower()

    for pattern in junk_patterns:
        if re.search(pattern, lowered):
            return ""

    line = re.sub(r"[|•©®™]", "", line)
    line = re.sub(r"\s+", " ", line).strip()

    line = line.strip("+-_=~:;,. ")

    if len(line) < 3:
        return ""

    if line.isdigit():
        return ""

    return line


def infer_superfaction(zip_name):
    name = zip_name.lower()

    if "xenos" in name:
        return "Xenos"

    if "imperium" in name:
        return "Imperium"

    if "chaos" in name:
        return "Chaos"

    return ""


def infer_faction_from_video(video_name):
    text = video_name.lower()

    faction_rules = [
        ("adeptus astartes", "Adeptus Astartes"),
        ("space marine", "Adeptus Astartes"),
        ("ultramarines", "Adeptus Astartes"),
        ("blood angels", "Adeptus Astartes"),
        ("space wolves", "Adeptus Astartes"),
        ("raven guard", "Adeptus Astartes"),
        ("imperial fists", "Adeptus Astartes"),
        ("black templar", "Adeptus Astartes"),
        ("white scar", "Adeptus Astartes"),
        ("iron hands", "Adeptus Astartes"),
        ("deathwatch", "Adeptus Astartes"),
        ("grey knights", "Grey Knights"),
        ("astra militarum", "Astra Militarum"),
        ("cadian", "Astra Militarum"),
        ("kasrkin", "Astra Militarum"),
        ("karskin", "Astra Militarum"),
        ("adeptus custodes", "Adeptus Custodes"),
        ("adeptus sororitas", "Adeptus Sororitas"),
        ("adeptus mechanicus", "Adeptus Mechanicus"),
        ("agents of the imperium", "Agents of the Imperium"),
        ("tyranids", "Tyranids"),
        ("ork", "Orks"),
        ("necrons", "Necrons"),
        ("aeldari", "Aeldari"),
        ("drukhari", "Drukhari"),
        ("genestealer cults", "Genestealer Cults"),
        ("leagues of votann", "Leagues of Votann"),
        ("t'au", "T'au Empire"),
        ("tau", "T'au Empire"),
    ]

    for key, faction in faction_rules:
        if key in text:
            return faction

    return ""


def infer_subfactions_from_video(video_name):
    known = [
        "Alaitoc",
        "Biel-Tan",
        "Harlequins",
        "Iyanden",
        "Saim-Hann",
        "Ulthwe",
        "Black Descent",
        "Coven of Twelve",
        "Cult of Red Grief",
        "Cult of Strife",
        "Cult of the Cursed Blade",
        "Kabal of Black Heart",
        "Kabal of the Black Heart",
        "Kabal of Flayed Skull",
        "Kabal of the Flayed Skull",
        "Kabal of Obsidian Rose",
        "Kabal of the Obsidian Rose",
        "Kabal of Poisoned Tongue",
        "Kabal of the Poisoned Tongue",
        "Prophets of Flesh",
        "Au'taal Sept",
        "Farsight Enclaves",
        "N'dras Sept",
        "T'au Sept",
        "Vior'la Sept",
        "Hive Fleet Behemoth",
        "Hive Fleet Gorgon",
        "Hive Fleet Hydra",
        "Hive Fleet Kraken",
        "Hive Fleet Leviathan",
        "Hive Fleet Tiamet",
        "Bad Moons",
        "Beastsnaggas",
        "Deathskulls",
        "Evil Sunz",
        "Freebooterz",
        "Goffs",
        "Snakebites",
        "Cult of the Four-Armed Emperor",
        "Raven Guard",
        "Imperial Fists",
        "Ultramarines",
        "White Scars",
        "Grey Knights",
        "Salamanders",
        "Iron Hands",
        "Deathwatch",
        "Black Templars",
        "Blood Angels",
        "Space Wolves",
        "Cadian",
        "Shadowkeepers",
        "Solar Watch",
        "Order of Our Martyred Lady",
        "Order of the Bloody Rose",
        "Regimental Support",
        "Tanith First and Only",
        "Tempestus Scions",
        "Adeptus Arbites",
        "Imperial Navy Breachers",
        "Inquisition",
        "Officio Assassinorum",
    ]

    found = []

    lowered = video_name.lower()

    for item in known:
        if item.lower() in lowered:
            found.append(item)

    return "; ".join(found)


def extract_zip(zip_path, destination):
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        for index, info in enumerate(z.infolist(), start=1):
            if info.is_dir():
                continue

            original_name = Path(info.filename).name
            suffix = Path(original_name).suffix.lower()

            if suffix not in VIDEO_SUFFIXES:
                continue

            safe_video_name = f"video_{index:03d}{suffix}"
            target_path = destination / safe_video_name

            with z.open(info) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def find_videos(folder):
    return [
        path for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    ]


def video_duration(video_path):
    output = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ])

    try:
        return float(output.strip())
    except Exception:
        return 0.0


def sample_times(duration):
    if duration <= 0:
        return []

    if duration <= 10:
        points = [0.20, 0.50, 0.80]
    elif duration <= 30:
        points = [0.12, 0.28, 0.44, 0.60, 0.76, 0.92]
    else:
        points = [0.08, 0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.88, 0.96]

    return [
        max(0.5, min(duration - 0.5, duration * p))
        for p in points
    ]


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
    return run([
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        str(image_path),
        "stdout",
        "--psm",
        "6",
    ])


def process_video(zip_name, video_path):
    duration = video_duration(video_path)
    times = sample_times(duration)

    records = []

    video_key = safe_name(video_path.stem)

    superfaction = infer_superfaction(zip_name)
    faction = infer_faction_from_video(video_path.name)
    subfactions = infer_subfactions_from_video(video_path.name)

    for index, timestamp in enumerate(times, start=1):
        frame_path = FRAME_DIR / video_key / f"frame_{index:03d}.png"

        extract_frame(
            video_path=video_path,
            timestamp=timestamp,
            output_path=frame_path,
        )

        if not frame_path.exists():
            continue

        text = ocr_image(frame_path)

        text_file = TEXT_DIR / f"{video_key}_frame_{index:03d}.txt"
        text_file.parent.mkdir(parents=True, exist_ok=True)
        text_file.write_text(text, encoding="utf-8")

        for raw_line in text.splitlines():
            candidate = clean_candidate_line(raw_line)

            if not candidate:
                continue

            records.append({
                "Candidate_Name": candidate,
                "Superfaction": superfaction,
                "Faction": faction,
                "Subfactions_From_Source_Video": subfactions,
                "Source_ZIP": zip_name,
                "Source_Video": video_path.name,
                "Frame_File": str(frame_path),
                "Timestamp_Seconds": round(timestamp, 2),
                "Verification_Status": "Needs Human Verification",
                "Approved_Name": "",
                "Approved_Faction": "",
                "Approved_Subfaction": "",
                "Approved_Unit_Type": "",
                "Notes": "OCR candidate extracted from source app video frame. Do not merge until approved.",
            })

    return records


def main():
    print("=" * 60)
    print("BUILD VERIFIED CATALOG CANDIDATES FROM VIDEOS V1")
    print("=" * 60)

    if not SOURCE_ZIP_DIR.exists():
        print()
        print("Missing folder:")
        print(SOURCE_ZIP_DIR)
        print()
        print("Put your reference ZIPs here:")
        print(SOURCE_ZIP_DIR)
        return

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

        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_zip(zip_path, extract_dir)

        videos = find_videos(extract_dir)

        print(f"Videos found: {len(videos)}")

        for video_path in videos:
            print(f"  Processing: {video_path.name}")

            records = process_video(
                zip_name=zip_path.name,
                video_path=video_path,
            )

            all_records.extend(records)

    if not all_records:
        print("No candidate names extracted.")
        return

    with CANDIDATE_OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
        writer.writeheader()
        writer.writerows(all_records)

    unique = {}

    for record in all_records:
        key = (
            record["Candidate_Name"].lower(),
            record["Faction"],
            record["Source_Video"],
        )

        if key not in unique:
            unique[key] = record

    unique_records = list(unique.values())

    with UNIQUE_OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=unique_records[0].keys())
        writer.writeheader()
        writer.writerows(unique_records)

    print()
    print("SUMMARY")
    print("-" * 60)
    print(f"Raw candidate rows ........ {len(all_records)}")
    print(f"Unique candidate rows ..... {len(unique_records)}")
    print()
    print("Written:")
    print(CANDIDATE_OUTPUT)
    print(UNIQUE_OUTPUT)
    print()
    print("=" * 60)
    print("CATALOG CANDIDATE BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()