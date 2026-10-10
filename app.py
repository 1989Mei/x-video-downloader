#!/usr/bin/env python3
"""x-video-downloader — a local web UI for downloading X (Twitter) videos.

Standard library only. Run `run.bat` (Windows) or `./run.sh` (macOS/Linux),
or simply `python app.py`.

For personal backup / research use only.
"""

import json
import mimetypes
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core import __version__
from core import config as cfgmod
from core import ytdlp
from core.config import free_port
from core.tasks import TaskManager
from core.util import clean_temp_files, human_size, reveal, scan_temp_files

WEB = cfgmod.WEB_DIR
TOKEN = secrets.token_urlsafe(24)
CTX = {}

TWEET_RE = None
import re  # noqa: E402

TWEET_RE = re.compile(r"(?:twitter\.com|x\.com)/[^/]+/status/\d+")


# --------------------------------------------------------------------------- #
# Startup banner + dependency self-check
# --------------------------------------------------------------------------- #
def install_hint(tool):
    win = sys.platform.startswith("win")
    mac = sys.platform == "darwin"
    if tool == "yt-dlp":
        if mac:
            return ["brew install yt-dlp", "pipx install yt-dlp", "pip install -U yt-dlp"]
        if win:
            return ["pip install -U yt-dlp", "winget install yt-dlp", "scoop install yt-dlp"]
        return ["pip install -U yt-dlp", "sudo apt install yt-dlp  # or your package manager"]
    if mac:
        return ["brew install ffmpeg"]
    if win:
        return ["winget install Gyan.FFmpeg", "scoop install ffmpeg"]
    return ["sudo apt install ffmpeg  # or your package manager"]


def banner(cfg):
    print("=" * 64)
    print(f"  x-video-downloader {__version__}")
    print("  Local web UI for downloading X (Twitter) videos")
    print("=" * 64)

    ytdlp_cmd = ytdlp.find_ytdlp()
    if not ytdlp_cmd:
        print("\n[ERROR] yt-dlp was not found.\n")
        print("Install it with any of the following, then run this again:\n")
        for h in install_hint("yt-dlp"):
            print(f"    {h}")
        print("\nDocs: https://github.com/yt-dlp/yt-dlp#installation")
        return None
    CTX["ytdlp"] = ytdlp_cmd
    CTX["ytdlpVersion"] = ytdlp.version(ytdlp_cmd)

    ffmpeg = ytdlp.find_ffmpeg()
    CTX["ffmpeg"] = ffmpeg

    print(f"\n  yt-dlp     : {CTX['ytdlpVersion']}")
    print(f"  yt-dlp from: {ytdlp.describe(ytdlp_cmd)}")
    print(f"  ffmpeg     : {ffmpeg or 'NOT FOUND'}")
    print(f"  output dir : {cfg['outdir']}")
    print(f"  proxy      : {cfg['proxy'] or 'not set (will try a direct connection)'}")
    print(f"  cookies    : {cfg['cookies_browser'] or 'off'}")
    if not ffmpeg:
        print("\n  [WARN] ffmpeg not found — video and audio cannot be merged.")
        print("         Install it with any of:")
        for h in install_hint("ffmpeg"):
            print(f"           {h}")
    if not cfg["proxy"]:
        print("\n  [WARN] No proxy detected. X is not reachable from some networks.")
        print("         Start your proxy, or pass --proxy http://127.0.0.1:7890")
    return ytdlp_cmd


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"x-video-downloader/{__version__}"

    # ---- plumbing ---- #
    def log_message(self, *args):
        pass

    def _send(self, code, payload, ctype="application/json; charset=utf-8"):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload, ensure_ascii=False)
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            pass

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if n <= 0 or n > 1_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _authorised(self):
        """Guard against other web pages POSTing into our localhost port.

        A cross-origin page cannot read our token, and cannot send a custom
        header without a CORS preflight we never approve.
        """
        origin = self.headers.get("Origin")
        if origin:
            host = (urlparse(origin).hostname or "").lower()
            if host not in ("127.0.0.1", "localhost", "::1"):
                return False
        return secrets.compare_digest(self.headers.get("X-XDL-Token") or "", TOKEN)

    # ---- routes ---- #
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_index()
            return
        if path.startswith("/web/"):
            self._serve_static(path)
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return

        if not self._authorised():
            self._send(403, {"ok": False, "code": "FORBIDDEN"})
            return

        if path == "/api/meta":
            cfg = CTX["cfg"]
            self._send(200, {
                "ok": True,
                "version": __version__,
                "ytdlpVersion": CTX.get("ytdlpVersion", "?"),
                "ytdlpSource": ytdlp.describe(CTX.get("ytdlp")),
                "ytdlpBundled": ytdlp.is_self_contained(CTX.get("ytdlp")),
                "ffmpeg": bool(CTX.get("ffmpeg")),
                "proxy": cfg["proxy"],
                "outdir": cfg["outdir"],
                "cookies": cfg["cookies_browser"],
                "fragments": cfg["concurrent_fragments"],
                "autoClean": cfg["auto_clean_temp"],
                "platform": sys.platform,
                "frozen": cfgmod.IS_FROZEN,
            })
            return

        if path == "/api/scan":
            outdir = (parse_qs(parsed.query).get("outdir") or [""])[0] \
                or CTX["cfg"]["outdir"]
            count, size = scan_temp_files(outdir)
            self._send(200, {"ok": True, "count": count, "bytes": size,
                             "sizeText": human_size(size) if size else "",
                             "outdir": outdir})
            return

        if path == "/api/tasks":
            self._send(200, {"ok": True, "tasks": CTX["mgr"].all()})
            return

        if path == "/api/task":
            tid = (parse_qs(parsed.query).get("id") or [""])[0]
            task = CTX["mgr"].get(tid)
            if not task:
                self._send(404, {"ok": False, "code": "NO_TASK"})
            else:
                self._send(200, {"ok": True, "task": task})
            return

        self._send(404, {"ok": False, "code": "NOT_FOUND"})

    def do_POST(self):
        if not self._authorised():
            self._send(403, {"ok": False, "code": "FORBIDDEN"})
            return

        path = urlparse(self.path).path
        body = self._read_body()
        cfg = CTX["cfg"]

        if path == "/api/parse":
            url = str(body.get("url") or "").strip()
            cookies = str(body.get("cookies") or cfg["cookies_browser"] or "")
            if not url:
                self._send(400, {"ok": False, "code": "NO_URL"})
                return
            if not TWEET_RE.search(url):
                self._send(400, {"ok": False, "code": "BAD_URL"})
                return
            try:
                info = ytdlp.probe(CTX["ytdlp"], url, proxy=cfg["proxy"], cookies=cookies)
                data = ytdlp.summarize(info, has_ffmpeg=bool(CTX.get("ffmpeg")))
                data["url"] = url
                self._send(200, {"ok": True, **data})
            except ytdlp.YtdlpError as e:
                self._send(200, {"ok": False, "code": "PARSE_FAILED", "detail": str(e)})
            except Exception as e:
                self._send(200, {"ok": False, "code": "PARSE_FAILED",
                                 "detail": f"{type(e).__name__}: {e}"})
            return

        if path == "/api/download":
            url = str(body.get("url") or "").strip()
            fmt_id = str(body.get("formatId") or "").strip()
            if not url or not fmt_id:
                self._send(400, {"ok": False, "code": "BAD_REQUEST"})
                return
            outdir = str(body.get("outdir") or cfg["outdir"]).strip() or cfg["outdir"]
            tid = CTX["mgr"].submit(
                url=url, fmt_id=fmt_id,
                needs_audio=bool(body.get("needsAudio")),
                audio_id=body.get("audioId"),
                outdir=outdir,
                title=str(body.get("title") or ""),
            )
            self._send(200, {"ok": True, "taskId": tid})
            return

        if path == "/api/cancel":
            tid = str(body.get("taskId") or "")
            ok = CTX["mgr"].cancel(tid)
            self._send(200, {"ok": ok})
            return

        if path == "/api/clear":
            CTX["mgr"].clear_finished()
            self._send(200, {"ok": True})
            return

        if path == "/api/update":
            if ytdlp.is_self_contained(CTX.get("ytdlp")):
                self._send(200, {"ok": False, "code": "BUNDLED",
                                 "version": CTX.get("ytdlpVersion", "?")})
                return
            ok, message = ytdlp.update(CTX["ytdlp"])
            CTX["ytdlpVersion"] = ytdlp.version(CTX["ytdlp"])
            tail = [l for l in (message or "").splitlines() if l.strip()][-4:]
            self._send(200, {"ok": ok, "version": CTX["ytdlpVersion"],
                             "detail": "\n".join(tail)})
            return

        if path == "/api/clean":
            outdir = str(body.get("outdir") or CTX["cfg"]["outdir"]).strip() \
                or CTX["cfg"]["outdir"]
            count, size = clean_temp_files(outdir)
            self._send(200, {"ok": True, "count": count, "bytes": size,
                             "sizeText": human_size(size) if size else "",
                             "outdir": outdir})
            return

        if path == "/api/open":
            target = str(body.get("path") or "").strip()
            if target and Path(target).exists():
                self._send(200, {"ok": reveal(target)})
            else:
                self._send(200, {"ok": False, "code": "NO_PATH"})
            return

        self._send(404, {"ok": False, "code": "NOT_FOUND"})

    # ---- static files ---- #
    def _serve_index(self):
        try:
            html = (WEB / "index.html").read_text(encoding="utf-8")
        except FileNotFoundError:
            self._send(500, "web/index.html is missing", "text/plain; charset=utf-8")
            return
        html = html.replace("__XDL_TOKEN__", TOKEN)
        self._send(200, html, "text/html; charset=utf-8")

    def _serve_static(self, path):
        rel = path[len("/web/"):]
        target = (WEB / rel).resolve()
        try:
            target.relative_to(WEB.resolve())
        except ValueError:
            self._send(403, {"ok": False, "code": "FORBIDDEN"})
            return
        if not target.is_file():
            self._send(404, {"ok": False, "code": "NOT_FOUND"})
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",
                                                  "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)


# --------------------------------------------------------------------------- #
def main(argv=None):
    # A frozen build bundles yt-dlp as a module and re-invokes itself to act as
    # the yt-dlp CLI. This must happen before any output or server startup.
    if len(sys.argv) > 1 and sys.argv[1] == ytdlp.SELF_YTDLP_FLAG:
        return ytdlp.run_as_ytdlp(sys.argv[2:])

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    cfg = cfgmod.load(argv)
    if cfgmod.ensure_config_file():
        pass  # config.json created on first run

    cmd = banner(cfg)
    if not cmd:
        try:
            input("\nPress Enter to exit...")
        except EOFError:
            pass
        return 1

    CTX["cfg"] = cfg
    CTX["mgr"] = TaskManager(cmd, proxy=cfg["proxy"],
                             cookies=cfg["cookies_browser"],
                             fragments=cfg["concurrent_fragments"],
                             auto_clean=cfg["auto_clean_temp"])

    port = free_port(cfg["port"])
    url = f"http://127.0.0.1:{port}/"

    print(f"\n  open:  {url}")
    print("\n  Close this window to stop the server.")
    print("  For personal backup / research use only.\n")
    print("=" * 64)

    if cfg["open_browser"]:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
