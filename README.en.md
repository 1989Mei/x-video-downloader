# X Video Downloader

<p align="center">
  <a href="README.md">中文</a> | <b>English</b>
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="X Video Downloader — UI preview" width="780">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platforms">
  <img src="https://img.shields.io/badge/dependencies-yt--dl%20only-success.svg" alt="Dependencies">
</p>

---

> ## ⚠️ Disclaimer
>
> This tool is intended for **personal backup and research use only**.
>
> - Downloaded content remains the property of its original authors and platform
> - You must comply with X's Terms of Service and the laws of your jurisdiction
> - **Do not** use it to infringe copyright, redistribute commercially, or for any unlawful purpose
>
> You are solely responsible for how you use this software. The author accepts no
> liability for misuse. **If you are unsure whether a use case is legitimate, don't do it.**

---

## What it is

A small local web app that runs on **your own machine**. Paste an X (Twitter) post URL,
see every available quality, pick one, and download it.

No X login. No API keys. Nothing is sent to a third-party server.

```
paste a link  →  parse qualities  →  pick one  →  queue it  →  open the folder
```

## Features

| | |
|---|---|
| 🎛 **Visual quality picker** | Grouped by resolution, with real file sizes and a suggested tier |
| 🔊 **Automatic A/V merge** | X's HLS streams are video-only; audio is added and merged for you |
| ⚡ **Concurrent fragments** | 4 parallel fragments by default — measured ~60× faster than a single thread (16 KB/s → 1.1 MB/s) |
| 🍪 **Browser cookies** | Works with protected and age-restricted posts |
| 📋 **Download queue** | Queue several jobs; cancel any of them at any time |
| 🔄 **One-click yt-dlp update** | X changes often — stay current so extraction keeps working |
| 🌏 **Bilingual UI** | Chinese / English, one click in the top-right corner |
| 🔒 **Guard rails on the local API** | Random token + Origin check so other web pages can't drive it |
| 📦 **Almost zero dependencies** | Backend is pure standard library; the only dependency is yt-dlp |

---

## Quick start

**Requirements:** Python 3.9+ and ffmpeg

### Windows

Just double-click `run.bat`. It finds Python automatically and only installs yt-dlp
when no working copy can be found at all.

### macOS / Linux

```bash
chmod +x run.sh
./run.sh
```

Or launch it directly:

```bash
pip install -U yt-dlp
python app.py
```

A `config.json` is created in the current directory on first run, and your browser
opens automatically.

### Installing ffmpeg

| Platform | Command |
|---|---|
| Windows | `winget install Gyan.FFmpeg` or `scoop install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Debian / Ubuntu | `sudo apt install ffmpeg` |

> ffmpeg is only needed to **merge audio and video**. Without it, video still
> downloads, but video-only formats end up silent — the startup log says so explicitly.

---

## Usage

1. **Paste a post URL** and hit **Parse**
   (both `x.com/...` and `twitter.com/...` work)
2. **Pick a quality** — the one marked **Best** is the suggested default
3. **Choose a browser cookie source** if the post is protected
4. **Confirm the output folder** (it is remembered for next time)
5. Hit **Add to queue**

Jobs run one at a time. When a job finishes you can jump straight to the file.

---

## A note on quality options (worth reading)

X serves each video in **two flavours**, and the size difference is large:

| Type | Description | Relative size |
|---|---|---|
| **HLS** | Adaptive-bitrate segments, efficient | small |
| **HTTP** | Progressive MP4, near-original bitrate | about **4×** |

Same 720p picture: HLS ≈ 1.16 GB, HTTP ≈ 3.99 GB.

**Rule of thumb:**

- **Interviews, talk shows, film, voice-over** → pick **HLS**. Visually indistinguishable, saves more than half the space.
- **Frames full of text or charts, or frame-by-frame inspection** → reach for **HTTP**.

**How "Best" is chosen:** the highest resolution whose estimated total size stays under
1.5 GB, so short clips suggest 1080p while a 4-hour stream drops to 720p automatically.

---

## CLI options

```
python app.py [options]

  --port N          listen port (default 8765, auto-increments if busy)
  --outdir PATH     download directory (default ~/Downloads)
  --proxy URL       HTTP proxy, e.g. http://127.0.0.1:7890 (default: auto-detect)
  --cookies NAME    reuse browser cookies: chrome / edge / firefox / brave / safari
  --fragments N     concurrent fragments, 1–16 (default 4)
  --no-browser      do not open the browser on start
  --version         print version
```

Environment variables are also supported: `XDL_OUTDIR`, `XDL_PROXY`, `XDL_PORT`,
`XDL_COOKIES`, `XDL_FRAGMENTS`, `XDL_OPEN_BROWSER`.

**Priority:** defaults → `config.json` → environment → CLI flags.

### Doing it manually with yt-dlp

This tool simply drives yt-dlp. If you would rather type the commands yourself:

```bash
# 1) list formats
yt-dlp --proxy http://127.0.0.1:7890 -F "https://x.com/user/status/1234567890"

# 2) download a specific one
yt-dlp --proxy http://127.0.0.1:7890 \
  --concurrent-fragments 4 --fragment-retries 25 --retries 25 \
  -f "hls-506+hls-audio-128000-Audio" \
  --merge-output-format mp4 \
  -o "out/%(uploader_id)s_%(id)s.%(ext)s" \
  "https://x.com/user/status/1234567890"
```

> ⚠️ **The classic gotcha:** on X, `hls-*` formats are **video-only**. You must append an
> audio format with `+`, otherwise the result has no sound. `http-*` formats already
> include audio.

---

## Configuration file

`config.json` (created automatically on first run):

```json
{
  "outdir": "",
  "proxy": "",
  "port": 8765,
  "cookies_browser": "",
  "concurrent_fragments": 4,
  "open_browser": true
}
```

| Field | Meaning |
|---|---|
| `outdir` | Empty means `~/Downloads` |
| `proxy` | Empty means auto-detect common local proxy ports |
| `cookies_browser` | Empty means no cookies by default |

---

## FAQ

**Parse fails or hangs** — X needs a proxy on some networks. The startup log prints the
detected proxy; pass `--proxy` if detection misses.

**The video has no sound** — You picked a video-only format and the audio merge failed,
usually because **ffmpeg is missing**. Check the `ffmpeg` line in the startup log.

**"No video could be found"** — This post has no video (text or image only). Quote tweets
and retweets sometimes behave the same way.

**Protected / age-restricted posts fail** — Pick the browser you are logged into under
"Browser cookies". Ideally keep that browser from fully exiting during the download.

**A download was interrupted** — Just queue the same job again; it **resumes** from the
existing fragments. ⚠️ Do not delete the `.part` and `Frag*` files.

**Speed is unstable** — That is your proxy's bandwidth. Tune concurrency with
`--fragments` (default 4, max 16).

**Port already in use** — The app walks forward to the next free port; check the startup
window for the actual address. You can also set `--port`.

**Why does a local server need a token?** — So that other web pages cannot silently POST
to `127.0.0.1` and make your machine download files. The token is random per run and is
only injected into the served page.

**Platform support** — Windows is well tested. The macOS / Linux code paths exist
(paths, folder reveal, launcher script) but are **not yet verified on real hardware** —
please open an issue if something breaks.

---

## Project structure

```
x-video-downloader/
├── app.py              # entry point: HTTP server and routes
├── core/
│   ├── config.py       # config loading + proxy detection
│   ├── ytdlp.py        # locate / version / update / probe / command building
│   ├── tasks.py        # download queue and cancellation
│   └── util.py         # cross-platform helpers
├── web/
│   ├── index.html
│   ├── style.css
│   └── app.js          # front-end logic + the zh/en dictionary
├── run.bat / run.sh
├── config.example.json
└── requirements.txt
```

Deliberately **no framework and no build step** — clone it and run it, and it stays easy
to adapt to your own needs.

---

## Contributing

Issues and PRs are welcome. Before submitting, please make sure:

- No new third-party dependencies are introduced (unless there is a good reason)
- You actually ran it on Windows after your change

---

## License

[MIT](LICENSE) © 2026 1989Mei
