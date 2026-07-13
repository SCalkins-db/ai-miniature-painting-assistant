from pathlib import Path
import subprocess
import time
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMMANDS = [
    ("Database Health", ["python", "-m", "src.database.database_health"]),
    ("Acquisition Doctor", ["python", "-m", "src.scripts.acquisition_doctor"]),
    ("Acquisition Pipeline", ["python", "-m", "src.scripts.run_acquisition_pipeline"]),
    ("Knowledge Metrics", ["python", "-m", "src.scripts.knowledge_engine_status"]),
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def draw_dashboard(results, current_stage, start_time):
    clear()

    print("=" * 60)
    print("FULL MVP PIPELINE")
    print("=" * 60)
    print()

    for i, (label, _) in enumerate(COMMANDS):

        if i < len(results):
            passed = results[i][1]

            if passed:
                print(f"{label:<28} ✓ PASS")
            else:
                print(f"{label:<28} ✗ FAILED")

        elif i == current_stage:
            print(f"{label:<28} ████████████████████ RUNNING")

        else:
            print(f"{label:<28} Waiting...")

    print()
    print("-" * 60)
    print(f"Elapsed: {time.perf_counter() - start_time:0.1f}s")
    print("=" * 60)
    print()


def run_step(label, command):

    print("=" * 60)
    print(label.upper())
    print("=" * 60)

    start = time.perf_counter()

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True
    )

    elapsed = time.perf_counter() - start

    return result.returncode == 0, elapsed


def main():

    total_start = time.perf_counter()

    results = []

    for stage_index, (label, command) in enumerate(COMMANDS):

        draw_dashboard(results, stage_index, total_start)

        passed, elapsed = run_step(label, command)

        results.append((label, passed, elapsed))

        if not passed:
            break

    clear()

    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print()

    for label, passed, elapsed in results:

        status = "PASS" if passed else "FAIL"

        print(f"{label:<30} {status:<6} {elapsed:8.2f}s")

    print()

    total = time.perf_counter() - total_start

    print("-" * 60)
    print(f"Elapsed Time : {total:.2f}s")

    if all(r[1] for r in results):
        print("Overall      : SUCCESS")
    else:
        print("Overall      : FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()