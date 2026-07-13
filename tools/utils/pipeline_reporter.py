from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StageStatus:
    name: str
    total: int = 100
    current: int = 0
    status: str = "WAITING"  # WAITING, RUNNING, PASS, COMPLETE, FAILED, WARNING
    current_file: str = ""
    notes: str = ""
    started_at: float | None = None
    finished_at: float | None = None
    metrics: dict[str, int | str | float] = field(default_factory=dict)


class PipelineReporter:
    def __init__(self, title: str = "FULL MVP PIPELINE", width: int = 40):
        self.title = title
        self.width = width
        self.started_at = time.time()
        self.stages: dict[str, StageStatus] = {}

    def add_stage(self, key: str, name: str, total: int = 100):
        self.stages[key] = StageStatus(name=name, total=max(total, 1))

    def start_stage(self, key: str, total: int | None = None):
        stage = self.stages[key]
        stage.status = "RUNNING"
        stage.started_at = time.time()
        if total is not None:
            stage.total = max(total, 1)
        self.render()

    def update_stage(
        self,
        key: str,
        current: int,
        total: int | None = None,
        current_file: str | Path | None = None,
        notes: str = "",
        **metrics,
    ):
        stage = self.stages[key]
        stage.status = "RUNNING"
        stage.current = current

        if total is not None:
            stage.total = max(total, 1)

        if current_file:
            stage.current_file = Path(current_file).name

        if notes:
            stage.notes = notes

        if metrics:
            stage.metrics.update(metrics)

        self.render()

    def finish_stage(self, key: str, status: str = "COMPLETE", **metrics):
        stage = self.stages[key]
        stage.current = stage.total
        stage.status = status
        stage.finished_at = time.time()

        if metrics:
            stage.metrics.update(metrics)

        self.render()

    def fail_stage(self, key: str, notes: str = "", **metrics):
        stage = self.stages[key]
        stage.status = "FAILED"
        stage.finished_at = time.time()
        stage.notes = notes

        if metrics:
            stage.metrics.update(metrics)

        self.render()

    def render(self):
        self._clear_screen()

        print("=" * 60)
        print(self.title)
        print("=" * 60)
        print()

        for stage in self.stages.values():
            print(self._stage_line(stage))

            if stage.status == "RUNNING":
                if stage.current_file:
                    print(f"Current File: {stage.current_file}")
                if stage.notes:
                    print(f"Notes: {stage.notes}")
                if stage.metrics:
                    for key, value in stage.metrics.items():
                        print(f"{self._label(key)}: {value}")
                print()

        print("-" * 60)
        print(f"Elapsed: {self._fmt_time(time.time() - self.started_at)}")
        print("=" * 60)

    def final_report(self, title: str = "PIPELINE COMPLETE", overall_status: str = "SUCCESS"):
        self._clear_screen()

        print("=" * 60)
        print(title)
        print("=" * 60)
        print()
        print("STATUS")
        print("-" * 40)
        print(f"Overall Status...............{overall_status}")
        print(f"Elapsed Time.................{self._fmt_time(time.time() - self.started_at)}")
        print()

        for stage in self.stages.values():
            print("-" * 40)
            print(stage.name.upper())
            print("-" * 40)
            print(f"Status.......................{stage.status}")

            if stage.started_at and stage.finished_at:
                print(f"Time.........................{self._fmt_time(stage.finished_at - stage.started_at)}")

            if stage.metrics:
                for key, value in stage.metrics.items():
                    print(f"{self._label(key):.<30}{value}")

            if stage.notes:
                print(f"Notes........................{stage.notes}")

            print()

        print("=" * 60)
        print(overall_status)
        print("=" * 60)

    def _stage_line(self, stage: StageStatus) -> str:
        if stage.status in {"PASS", "COMPLETE"}:
            return f"{stage.name:<28} ✓ {stage.status}"

        if stage.status == "FAILED":
            return f"{stage.name:<28} ✗ FAILED"

        if stage.status == "WARNING":
            return f"{stage.name:<28} ! WARNING"

        if stage.status == "WAITING":
            return f"{stage.name:<28} Waiting..."

        percent = stage.current / stage.total
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        return (
            f"{stage.name:<28} "
            f"{bar} "
            f"{percent * 100:5.1f}% "
            f"{stage.current}/{stage.total}"
        )

    @staticmethod
    def _clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def _label(value: str) -> str:
        return value.replace("_", " ").title().replace("Ocr", "OCR")