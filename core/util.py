"""Cross-platform helpers (kept dependency-free)."""

import os
import subprocess
import sys
from pathlib import Path


def human_size(n):
    """Bytes -> '1.23 GB'."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n <= 0:
        return "?"
    for unit, div in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n} B"


def human_duration(sec):
    """Seconds -> '4 h 22 min' (language-neutral)."""
    try:
        sec = int(float(sec))
    except (TypeError, ValueError):
        return "?"
    if sec <= 0:
        return "?"
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def reveal(path):
    """Open the containing folder, selecting the file when the OS supports it."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if sys.platform.startswith("win"):
            if p.is_file():
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p if p.is_dir() else p.parent)])
        return True
    except Exception:
        return False


def no_window_kwargs():
    """On Windows, stop console windows from flashing for child processes."""
    if sys.platform.startswith("win"):
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}
