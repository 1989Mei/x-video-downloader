"""Sequential download queue with cancellation.

One worker thread consumes the queue, so a 4-hour stream never fights a
second job for bandwidth. Each task can be cancelled at any point; a running
download is terminated and its partial fragments are left on disk so a later
attempt can resume.
"""

import queue
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

from . import ytdlp
from .util import clean_temp_files, human_size, no_window_kwargs

PROG_RE = re.compile(r"^PROG\|(.*?)\|(.*?)\|(.*)$")

STAGE = {
    "queued": "queued",
    "downloading": "downloading",
    "merging": "merging",
    "done": "done",
    "error": "error",
    "canceled": "canceled",
}


class TaskManager:
    def __init__(self, cmd, proxy="", cookies="", fragments=4, log_limit=300,
                 auto_clean=True):
        self.cmd = cmd
        self.proxy = proxy
        self.cookies = cookies
        self.fragments = fragments
        self.log_limit = log_limit
        self.auto_clean = auto_clean

        self._q = queue.Queue()
        self._tasks = {}
        self._procs = {}
        self._lock = threading.Lock()

        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    # ---------------- public API ---------------- #
    def submit(self, url, fmt_id, needs_audio, audio_id, outdir, title="",
               audio_only=False, stem=""):
        tid = uuid.uuid4().hex[:12]
        task = {
            "id": tid,
            "url": url,
            "title": title,
            "formatId": fmt_id,
            "needsAudio": needs_audio,
            "audioId": audio_id,
            "audioOnly": audio_only,
            "stem": stem,
            "outdir": outdir,
            "status": "queued",
            "stage": "queued",
            "percent": "0%",
            "speed": "",
            "eta": "",
            "phase": 0,          # which stream is being fetched (video, then audio)
            "phaseTotal": 1,
            "file": "",
            "fileSize": "",
            "error": "",
            "selector": "",
            "createdAt": time.time(),
            "log": [],
            "_cancel_ev": threading.Event(),
        }
        with self._lock:
            self._tasks[tid] = task
        self._q.put(tid)
        return tid

    def get(self, tid):
        with self._lock:
            t = self._tasks.get(tid)
        return self._public(t) if t else None

    def all(self):
        with self._lock:
            items = list(self._tasks.values())
        items.sort(key=lambda t: t["createdAt"], reverse=True)
        return [self._public(t) for t in items]

    def cancel(self, tid):
        with self._lock:
            t = self._tasks.get(tid)
            if not t:
                return False
            t["_cancel_ev"].set()
            proc = self._procs.get(tid)

        if t["status"] == "queued":
            t["status"] = "canceled"
            t["stage"] = "canceled"

        if proc and proc.poll() is None:
            for killer in (proc.terminate, proc.kill):
                try:
                    killer()
                    break
                except Exception:
                    continue
        return True

    def clear_finished(self):
        with self._lock:
            for tid in [k for k, v in self._tasks.items()
                        if v["status"] in ("done", "error", "canceled")]:
                self._tasks.pop(tid, None)

    # ---------------- internals ---------------- #
    @staticmethod
    def _public(t):
        return {k: v for k, v in t.items() if not k.startswith("_")}

    def _loop(self):
        """Consume the queue forever.

        Deliberately catches BaseException: this thread dying would silently
        stall every job still waiting in the queue, which is far worse than
        swallowing an odd error.
        """
        while True:
            task = None
            try:
                tid = self._q.get()
                with self._lock:
                    task = self._tasks.get(tid)
                if task and task["status"] == "queued":
                    self._run(task)
            except BaseException as e:      # noqa: BLE001 - see docstring
                try:
                    if task is not None and task.get("status") not in (
                            "done", "error", "canceled"):
                        task["status"] = "error"
                        task["stage"] = "error"
                        task["error"] = f"{type(e).__name__}: {e}"
                except Exception:
                    pass
            finally:
                try:
                    self._q.task_done()
                except Exception:
                    pass

    def _run(self, task):
        tid = task["id"]
        ev = task["_cancel_ev"]

        task["status"] = "running"
        task["stage"] = "downloading"

        attempts = [self.cookies]
        if self.cookies:
            attempts.append("")  # fall back to no cookies if the browser lookup fails

        last_err = ""
        for attempt_cookies in attempts:
            if ev.is_set():
                break
            ok, err = self._attempt(task, attempt_cookies, ev)
            if ok:
                self._finish_ok(task)
                return
            last_err = err
            if ev.is_set():
                break
            # only retry without cookies when cookies were actually the problem
            if attempt_cookies and not _looks_like_cookie_error(err):
                break

        if ev.is_set():
            task["status"] = "canceled"
            task["stage"] = "canceled"
            task["percent"] = "0%"
            task["error"] = ""
        else:
            task["status"] = "error"
            task["stage"] = "error"
            task["error"] = last_err or "download failed"

        # A cancelled job leaves fragments behind. The user walked away from it,
        # so don't let them pile up. A *failed* job keeps them on purpose: those
        # fragments are what makes a retry resume instead of start over.
        if self.auto_clean and task["status"] == "canceled":
            self._cleanup(task)

    def _cleanup(self, task, timeout=20):
        """Delete yt-dlp temp files so the output folder keeps only finished files.

        The queue is sequential, so no other job can be mid-download in this
        directory while a job is wrapping up.

        Runs in a helper thread with a timeout: a filesystem that stalls on
        unlink (locked file, antivirus, network drive) must never wedge the
        worker and leave every later job stuck in the queue.
        """
        box = {}

        def work():
            try:
                box["r"] = clean_temp_files(task["outdir"])
            except Exception:
                box["r"] = (0, 0)

        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join(timeout)
        if th.is_alive():
            return

        count, freed = box.get("r", (0, 0))
        if count:
            task["cleanedFiles"] = count
            task["cleanedBytes"] = freed

    def _attempt(self, task, cookies, ev):
        args, selector = ytdlp.build_download_cmd(
            self.cmd, task["url"], task["formatId"], task["needsAudio"],
            task["audioId"], task["outdir"],
            proxy=self.proxy, cookies=cookies, fragments=self.fragments,
            audio_only=task.get("audioOnly", False),
            stem=task.get("stem", ""),
        )
        task["selector"] = selector
        # A selector like "hls-506+hls-audio-128000-Audio" means two separate
        # streams are fetched one after another. Each one reports its own 0-100%
        # progress, so the UI needs to say which pass it is on — otherwise the
        # bar visibly jumps backwards when the audio pass starts.
        task["phaseTotal"] = selector.count("+") + 1
        task["phase"] = 0

        try:
            Path(task["outdir"]).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"cannot create output directory: {e}"

        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="ignore", bufsize=1,
                **no_window_kwargs(),
            )
        except FileNotFoundError:
            return False, "yt-dlp executable not found"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

        with self._lock:
            self._procs[task["id"]] = proc

        try:
            for raw in proc.stdout:
                line = raw.rstrip("\r\n")
                if not line.strip():
                    continue
                task["log"].append(line)
                if len(task["log"]) > self.log_limit:
                    task["log"] = task["log"][-self.log_limit // 2:]

                m = PROG_RE.match(line)
                if m:
                    task["percent"] = m.group(1).strip()
                    task["speed"] = m.group(2).strip()
                    task["eta"] = m.group(3).strip()
                    task["stage"] = "downloading"
                    continue

                if "Destination:" in line:
                    task["phase"] = min(task.get("phase", 0) + 1,
                                        task.get("phaseTotal") or 1)
                    task["file"] = line.split("Destination:", 1)[1].strip().strip('"')
                elif "[Merger]" in line or "Merging formats" in line:
                    task["stage"] = "merging"
                    task["percent"] = "100%"
                    task["phase"] = task.get("phaseTotal") or 1
                    mm = re.search(r'"([^"]+\.mp4)"', line)
                    if mm:
                        task["file"] = mm.group(1)
                    elif " into " in line:
                        task["file"] = line.split(" into ", 1)[1].strip().strip('"')
                elif "has already been downloaded" in line:
                    # yt-dlp found the target filename already on disk and did
                    # nothing. That must not be reported as a fresh download.
                    task["percent"] = "100%"
                    task["skippedExisting"] = True
        finally:
            try:
                rc = proc.wait(timeout=600)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
                rc = -1
            with self._lock:
                self._procs.pop(task["id"], None)

        if ev.is_set():
            return False, ""

        if rc == 0:
            return True, ""

        errs = [l for l in task["log"] if "ERROR" in l]
        return False, (errs[-1] if errs else f"yt-dlp exited with code {rc}")

    def _finish_ok(self, task):
        task["status"] = "done"
        task["stage"] = "done"
        task["percent"] = "100%"
        task["speed"] = ""
        task["eta"] = ""

        fp = Path(task["file"]) if task.get("file") else None
        if not fp or not fp.exists():
            cands = sorted(
                Path(task["outdir"]).glob("*.mp4"),
                key=lambda f: f.stat().st_mtime, reverse=True,
            )
            fp = cands[0] if cands else None

        if fp and fp.exists():
            task["file"] = str(fp)
            task["fileSize"] = human_size(fp.stat().st_size)

        # Belt and braces: yt-dlp normally tidies up after itself, but if a
        # fragment survived an odd interruption the folder should still end up
        # containing nothing but the finished file.
        if self.auto_clean:
            self._cleanup(task)


def _looks_like_cookie_error(err):
    e = (err or "").lower()
    return any(k in e for k in ("cookie", "browser", "could not find", "permission"))
