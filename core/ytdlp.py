"""Locate yt-dlp / ffmpeg, probe media info, and build download commands."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config
from .util import no_window_kwargs

ROOT = Path(__file__).resolve().parent.parent

PROGRESS_TEMPLATE = (
    "PROG|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"
)

# Argument that makes the frozen executable behave as the yt-dlp CLI.
SELF_YTDLP_FLAG = "--run-ytdlp"


class YtdlpError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Locating the binaries
# --------------------------------------------------------------------------- #
def find_ytdlp():
    """Return a command list for yt-dlp, or None.

    Order:
      1. a standalone binary the user dropped into <data>/bin (updatable)
      2. a project-local venv            (source mode)
      3. yt-dlp on PATH
      4. `python -m yt_dlp`              (source mode)
      5. the bundled module, via the frozen app re-invoking itself
    """
    for name in ("yt-dlp.exe", "yt-dlp"):
        p = config.BIN_DIR / name
        if p.exists():
            return [str(p)]

    if not config.IS_FROZEN:
        for rel in (
            Path(".venv/Scripts/yt-dlp.exe"),
            Path(".venv/bin/yt-dlp"),
            Path("venv/Scripts/yt-dlp.exe"),
            Path("venv/bin/yt-dlp"),
        ):
            p = ROOT / rel
            if p.exists():
                return [str(p)]

    found = shutil.which("yt-dlp")
    if found:
        return [found]

    if not config.IS_FROZEN:
        try:
            if importlib.util.find_spec("yt_dlp") is not None:
                return [sys.executable, "-m", "yt_dlp"]
        except Exception:
            pass

    # Frozen build: the module is bundled, so run ourselves as the yt-dlp CLI.
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, SELF_YTDLP_FLAG]
    except Exception:
        pass

    return None


def run_as_ytdlp(argv):
    """Entry point for `app --run-ytdlp ...` — delegate straight to yt-dlp."""
    import yt_dlp
    try:
        return yt_dlp.main(argv if argv else None)
    except SystemExit as e:
        return int(e.code or 0)


def describe(cmd):
    """Human-readable description of where yt-dlp came from."""
    if not cmd:
        return "not found"
    if SELF_YTDLP_FLAG in cmd:
        return "bundled with this app"
    if len(cmd) >= 3 and cmd[1] == "-m":
        return "python -m yt_dlp"
    p = Path(cmd[0])
    if p.exists() and p.parent == config.BIN_DIR:
        return f"downloaded copy ({p})"
    return str(p) if p.exists() else cmd[0]


def is_self_contained(cmd):
    """True when yt-dlp is bundled, so `-U` cannot really update anything."""
    return bool(cmd) and SELF_YTDLP_FLAG in cmd


def find_ffmpeg():
    for name in ("ffmpeg.exe", "ffmpeg"):
        p = config.BIN_DIR / name
        if p.exists():
            return str(p)
    found = shutil.which("ffmpeg")
    if found:
        return found
    for p in (
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("/usr/local/bin/ffmpeg"),
        Path("/opt/homebrew/bin/ffmpeg"),
        Path("/usr/bin/ffmpeg"),
    ):
        if p.exists():
            return str(p)
    return None


def run(cmd, timeout=None):
    """Run a command, capturing output as text."""
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="ignore", timeout=timeout,
        **no_window_kwargs(),
    )


def version(cmd):
    try:
        r = run(list(cmd) + ["--version"], timeout=30)
        v = (r.stdout or "").strip().splitlines()
        return v[0].strip() if v else "unknown"
    except Exception:
        return "unknown"


def update(cmd):
    """Try yt-dlp's self-updater, then fall back to pip.

    Returns (ok, message). A bundled yt-dlp has nothing to update in place —
    the caller should point the user at the Releases page instead.
    """
    if is_self_contained(cmd):
        return False, "bundled"

    out = ""
    try:
        r = run(list(cmd) + ["-U"], timeout=300)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0:
            return True, out
    except Exception:
        pass

    # The pip fallback needs a real interpreter; there is none in a frozen build.
    if config.IS_FROZEN:
        return False, out or "not updatable here"

    try:
        r = run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], timeout=600)
        out2 = ((r.stdout or "") + (r.stderr or "")).strip()
        return (r.returncode == 0), (out2 or out or "pip update attempted")
    except Exception as e:
        return False, f"{e}"


# --------------------------------------------------------------------------- #
# Probing
# --------------------------------------------------------------------------- #
def _net_flags(proxy="", cookies=""):
    flags = []
    if proxy:
        flags += ["--proxy", proxy]
    if cookies:
        flags += ["--cookies-from-browser", cookies]
    return flags


def _last_error(r):
    text = ((r.stderr or "") + "\n" + (r.stdout or "")).strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in reversed(lines):
        if "ERROR" in line:
            return line
    return lines[-1] if lines else "yt-dlp failed"


def probe(cmd, url, proxy="", cookies="", timeout=180):
    """Return yt-dlp's info dict for `url`."""
    args = (list(cmd) + ["--no-warnings"] + _net_flags(proxy, cookies)
            + ["-J", "--no-playlist", url])
    r = run(args, timeout=timeout)
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise YtdlpError(_last_error(r))
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise YtdlpError("could not parse yt-dlp output")


# --------------------------------------------------------------------------- #
# Format summarising — the part that makes the UI readable
# --------------------------------------------------------------------------- #
def summarize(info, has_ffmpeg=True):
    """Turn yt-dlp's format list into resolution groups for the UI.

    How formats look on X:
      * progressive  `http-*`  vcodec=None, acodec=None  -> already has audio
      * video only   `hls-*`   vcodec=avc1.., acodec='none' -> needs an audio track
      * audio only   `hls-audio-*-Audio`  vcodec='none'

    Without ffmpeg the two tracks cannot be merged, so only formats that already
    carry audio are recommended.
    """
    duration = info.get("duration") or 0
    formats = info.get("formats") or []

    audio_formats = [f for f in formats if f.get("vcodec") == "none"]
    video_formats = [f for f in formats if f.get("vcodec") != "none"]

    best_audio = max(audio_formats, key=lambda f: f.get("tbr") or 0, default=None)
    audio_id = best_audio.get("format_id") if best_audio else None
    audio_size = 0
    if best_audio:
        audio_size = int((best_audio.get("tbr") or 0) * 1000 / 8 * duration)

    by_height = {}
    for f in video_formats:
        by_height.setdefault(f.get("height") or 0, []).append(f)

    groups = []
    for height in sorted(by_height, reverse=True):
        options = []
        for f in by_height[height]:
            needs_audio = (f.get("acodec") == "none")
            size = f.get("filesize") or f.get("filesize_approx")
            if not size:
                size = int((f.get("tbr") or 0) * 1000 / 8 * duration)
            total = int(size) + (audio_size if needs_audio else 0)
            proto = "HLS" if str(f.get("protocol") or "").startswith("m3u8") else "HTTP"
            options.append({
                "id": f.get("format_id"),
                "protocol": proto,
                "efficient": proto == "HLS",
                "needsAudio": needs_audio,
                "needsFFmpeg": needs_audio and not has_ffmpeg,
                "audioId": audio_id if needs_audio else None,
                "size": total,
                "tbr": f.get("tbr") or 0,
            })
        options.sort(key=lambda o: o["size"])
        first = by_height[height][0]
        groups.append({
            "height": height,
            "width": first.get("width") or 0,
            "options": options,
        })

    # Recommend the highest resolution that stays under 1.5 GB, so short clips
    # get 1080p while multi-hour streams drop to a sane tier. Options that would
    # need ffmpeg are skipped when ffmpeg is missing. Fall back to the smallest
    # usable option available.
    usable = [
        o for g in groups for o in g["options"]
        if has_ffmpeg or not o["needsFFmpeg"]
    ]
    recommended = None
    for g in groups:
        for o in g["options"]:
            if o in usable and o["size"] <= 1.5 * 1024 ** 3:
                recommended = o["id"]
                break
        if recommended:
            break
    if not recommended and usable:
        recommended = min(usable, key=lambda o: o["size"])["id"]

    return {
        "id": info.get("id"),
        "title": info.get("title") or "(untitled)",
        "uploader": info.get("uploader") or info.get("uploader_id") or "",
        "uploaderId": info.get("uploader_id") or "",
        "duration": duration,
        "thumbnail": info.get("thumbnail") or "",
        "webpage": info.get("webpage_url") or "",
        "groups": groups,
        "audioOnly": ({"id": audio_id, "size": audio_size} if audio_id else None),
        "recommended": recommended,
        "hasFFmpeg": has_ffmpeg,
    }


# --------------------------------------------------------------------------- #
# Download command
# --------------------------------------------------------------------------- #
def build_download_cmd(cmd, url, fmt_id, needs_audio, audio_id, outdir,
                       proxy="", cookies="", fragments=4):
    selector = f"{fmt_id}+{audio_id}" if (needs_audio and audio_id) else fmt_id
    args = list(cmd) + ["--no-warnings", "--newline",
                        "--progress-template", PROGRESS_TEMPLATE]
    args += _net_flags(proxy, cookies)
    args += [
        "--concurrent-fragments", str(fragments),
        "--fragment-retries", "25",
        "--retries", "25",
        "-f", selector,
        "--merge-output-format", "mp4",
        "-o", os.path.join(outdir, "%(uploader_id)s_%(id)s.%(ext)s"),
        url,
    ]
    return args, selector
