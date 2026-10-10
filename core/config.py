"""Configuration loading.

Priority (low -> high):
    built-in defaults  ->  config.json  ->  environment variables  ->  CLI flags
"""

import argparse
import json
import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "outdir": "",                 # empty -> ~/Downloads
    "proxy": "",                  # empty -> auto-detect
    "port": 8765,
    "cookies_browser": "",        # "" | chrome | edge | firefox | brave | safari | chromium
    "concurrent_fragments": 4,
    "open_browser": True,
}

# environment variable -> config key
ENV_MAP = {
    "XDL_OUTDIR": "outdir",
    "XDL_PROXY": "proxy",
    "XDL_PORT": "port",
    "XDL_COOKIES": "cookies_browser",
    "XDL_FRAGMENTS": "concurrent_fragments",
    "XDL_OPEN_BROWSER": "open_browser",
}

# Common local HTTP-proxy ports (Clash / Clash Verge / v2rayN / Surge / Nekoray ...).
# Deliberately excludes 8080 — too often used by unrelated dev servers.
PROXY_PORTS = [7890, 7897, 7891, 10809, 8889, 2080, 6152, 8118, 33210, 20171]


def default_outdir():
    return str(Path.home() / "Downloads")


def detect_proxy(timeout=0.3):
    """Return a local HTTP proxy URL if one is listening, else None."""
    for port in PROXY_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return f"http://127.0.0.1:{port}"
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
        val = os.environ.get(key)
        if val:
            return val
    return None


def _as_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() not in ("0", "false", "no", "off", "")


def ensure_config_file():
    """Create config.json on first run so users can find the knobs."""
    created = False
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULTS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        created = True
    return created


def load(argv=None):
    cfg = dict(DEFAULTS)

    # --- config.json ---
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[warn] could not read config.json, using defaults: {e}")

    # --- environment ---
    for env, key in ENV_MAP.items():
        if env in os.environ:
            cfg[key] = os.environ[env]

    # --- CLI ---
    ap = argparse.ArgumentParser(
        prog="x-video-downloader",
        description="Local web UI for downloading X (Twitter) videos. "
                    "For personal backup / research use only.",
    )
    ap.add_argument("--port", type=int, help=f"listen port (default {DEFAULTS['port']})")
    ap.add_argument("--outdir", help="download directory (default ~/Downloads)")
    ap.add_argument("--proxy", help="HTTP proxy URL, e.g. http://127.0.0.1:7890 "
                                    "(default: auto-detect)")
    ap.add_argument("--cookies", dest="cookies_browser",
                    choices=["", "chrome", "edge", "firefox", "brave", "safari", "chromium"],
                    help="reuse cookies from this browser (needed for protected/age-restricted posts)")
    ap.add_argument("--fragments", type=int, dest="concurrent_fragments",
                    help="concurrent HLS fragments (default 4)")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser on start")
    ap.add_argument("--version", action="store_true", help="print version and exit")

    args = ap.parse_args(argv)

    if args.version:
        from core import __version__
        print(f"x-video-downloader {__version__}")
        raise SystemExit(0)

    for key in ("port", "outdir", "proxy", "cookies_browser", "concurrent_fragments"):
        val = getattr(args, key, None)
        if val is not None:
            cfg[key] = val
    if args.no_browser:
        cfg["open_browser"] = False

    # --- normalise ---
    if not str(cfg.get("outdir") or "").strip():
        cfg["outdir"] = default_outdir()
    cfg["outdir"] = str(Path(cfg["outdir"]).expanduser())

    try:
        cfg["port"] = int(cfg["port"])
    except (TypeError, ValueError):
        cfg["port"] = DEFAULTS["port"]

    try:
        cfg["concurrent_fragments"] = max(1, min(16, int(cfg["concurrent_fragments"])))
    except (TypeError, ValueError):
        cfg["concurrent_fragments"] = DEFAULTS["concurrent_fragments"]

    cfg["open_browser"] = _as_bool(cfg["open_browser"])
    cfg["cookies_browser"] = str(cfg.get("cookies_browser") or "").strip().lower()
    cfg["proxy"] = str(cfg.get("proxy") or "").strip()
    if not cfg["proxy"]:
        cfg["proxy"] = detect_proxy() or ""

    return cfg


def free_port(start):
    """Find a free port starting at `start` (so two instances don't collide)."""
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start
