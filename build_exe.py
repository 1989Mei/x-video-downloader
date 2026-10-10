#!/usr/bin/env python3
"""Build a single-file executable for the current platform.

The bundle carries the whole app plus the yt-dlp Python package, so the result
runs on a machine with no Python and no yt-dlp installed. yt-dlp is invoked by
re-running the executable with the ``--run-ytdlp`` flag (see core/ytdlp.py).

Usage
-----
    pip install pyinstaller yt-dlp
    python build_exe.py

Output
------
    dist/x-video-downloader        (Linux / macOS)
    dist/x-video-downloader.exe    (Windows)
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "x-video-downloader"


def main():
    try:
        import PyInstaller.__main__  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed.\n\n    pip install pyinstaller yt-dlp\n")
        return 1

    try:
        import yt_dlp
        version = yt_dlp.version.__version__
    except ImportError:
        print("yt-dlp is not importable, so it cannot be bundled.\n\n"
              "    pip install -U yt-dlp\n")
        return 1

    sep = os.pathsep                      # ';' on Windows, ':' elsewhere
    exe = NAME + (".exe" if sys.platform.startswith("win") else "")

    print(f"Bundling x-video-downloader with yt-dlp {version}")
    print(f"Platform: {sys.platform}")
    print()

    args = [
        str(ROOT / "app.py"),
        "--name", NAME,
        "--onefile",
        "--console",
        "--noconfirm",
        "--clean",

        # ship the web UI next to the code
        "--add-data", f"{ROOT / 'web'}{sep}web",

        # yt-dlp lazy-loads its extractors, so collect them all explicitly
        "--collect-submodules", "yt_dlp",

        # keep the binary small — none of these are used
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",

        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]

    import PyInstaller.__main__ as pyi
    pyi.run(args)

    out = ROOT / "dist" / exe
    print()
    if out.exists():
        print(f"Built: {out}")
        print(f"Size : {out.stat().st_size / 1024 / 1024:.1f} MB")
        print()
        print("Run it by double-clicking, or from a terminal:")
        print(f"    {out}")
        return 0
    print("Build finished but the executable was not found — check the output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
