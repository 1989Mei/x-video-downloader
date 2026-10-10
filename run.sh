#!/usr/bin/env sh
# x-video-downloader launcher for macOS / Linux
set -e
cd "$(dirname "$0")"

# ---- locate python --------------------------------------------------------
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "[ERROR] Python 3.9+ was not found on PATH."
  echo "        macOS:  brew install python"
  echo "        Debian: sudo apt install python3 python3-pip"
  exit 1
fi

# ---- make sure yt-dlp is present -----------------------------------------
if [ ! -x ".venv/bin/yt-dlp" ] && ! "$PY" -c "import yt_dlp" >/dev/null 2>&1; then
  echo "Installing yt-dlp ..."
  "$PY" -m pip install -U yt-dlp
  echo
fi

# ---- run ------------------------------------------------------------------
exec "$PY" app.py "$@"
