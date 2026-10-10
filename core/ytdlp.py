"""Locate yt-dlp / ffmpeg, probe media info, and build download commands."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .util import no_window_kwargs

ROOT = Path(__file__).resolve().parent.parent

PROGRESS_TEMPLATE = (
    "PROG|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"
)


class YtdlpError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Locating the binaries
# --------------------------------------------------------------------------- #
def find_ytdlp():
    """Return a command list for yt-dlp, or None.

    Order: project-local venv -> PATH -> `python -m yt_dlp`.
    """
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

    try:
        if importlib.util.find_spec("yt_dlp") is not None:
            return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        pass

    return None


def find_ffmpeg():
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
    """Try yt-dlp's self-updater, then fall back to pip. Returns (ok, message)."""
    try:
        r = run(list(cmd) + ["-U"], timeout=300)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0:
            low = out.lower()
            if "up to date" in low or "already" in low:
                return True, out
            return True, out
    except Exception:
        out = ""

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
def summarize(info):
    """Turn yt-dlp's format list into resolution groups for the UI.

    How formats look on X:
      * progressive  `http-*`  vcodec=None, acodec=None  -> already has audio
      * video only   `hls-*`   vcodec=avc1.., acodec='none' -> needs an audio track
      * audio only   `hls-audio-*-Audio`  vcodec='none'
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
    # get 1080p while multi-hour streams drop to a sane tier. Fall back to the
    # smallest option available.
    recommended = None
    for g in groups:
        for o in g["options"]:
            if o["size"] <= 1.5 * 1024 ** 3:
                recommended = o["id"]
                break
        if recommended:
            break
    if not recommended and groups:
        recommended = min(
            (o for g in groups for o in g["options"]), key=lambda o: o["size"]
        )["id"]

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
