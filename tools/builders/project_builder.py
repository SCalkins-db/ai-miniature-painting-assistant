from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


BUILDER_COMMANDS = [
    ("Architecture Docs", ["python", "-m", "src.scripts.create_architecture_docs"]),
    ("Core Engine Modules", ["python", "-m", "src.scripts.build_core_engine_modules"]),
    ("Intelligence Layer", ["python", "-m", "src.scripts.build_intelligence_layer"]),
    ("Shop Tools", ["python", "-m", "src.scripts.build_shop_tools"]),
]


def run_command(label, command):
    print(f"\nRUNNING: {label}")
    print("-" * 60)

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )

        print(completed.stdout)

        if completed.returncode != 0:
            print(completed.stderr)
            print(f"FAILED: {label}")
            return False

        print(f"PASS: {label}")
        return True

    except Exception as error:
        print(f"FAILED: {label} -> {error}")
        return False


def main():
    print("=" * 60)
    print("PROJECT BUILDER")
    print("=" * 60)

    results = []

    for label, command in BUILDER_COMMANDS:
        results.append(run_command(label, command))

    print("\n" + "=" * 60)

    if all(results):
        print("PROJECT BUILDER STATUS: PASS")
    else:
        print("PROJECT BUILDER STATUS: FAIL")

    print("=" * 60)
    print("\nRecommended next commands:")
    print("python -m src.scripts.project_doctor")
    print("python -m src.scripts.project_inventory")
    print("python -m src.scripts.project_report")


if __name__ == "__main__":
    main()
