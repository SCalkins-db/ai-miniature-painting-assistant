from __future__ import annotations

import sys
import time
from pathlib import Path


class ProgressBar:
    def __init__(self, label: str, total: int, width: int = 30):
        self.label = label
        self.total = max(total, 1)
        self.width = width
        self.start_time = time.time()
        self.current = 0

    def update(self, current: int, current_file: str | Path | None = None):
        self.current = min(current, self.total)

        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0

        remaining = self.total - self.current
        eta = remaining / rate if rate > 0 else 0

        current_name = Path(current_file).name if current_file else ""

        line = (
            f"\r{self.label} "
            f"[{bar}] "
            f"{percent * 100:6.2f}% | "
            f"{self.current}/{self.total} | "
            f"elapsed {self._fmt_time(elapsed)} | "
            f"ETA {self._fmt_time(eta)}"
        )

        if current_name:
            line += f" | current: {current_name}"

        sys.stdout.write(line)
        sys.stdout.flush()

    def finish(self):
        self.update(self.total)
        sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(seconds)

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        if h:
            return f"{h}h {m:02d}m {s:02d}s"
        if m:
            return f"{m}m {s:02d}s"
        return f"{s}s"