# X Video Downloader

<p align="center">
  <b>中文</b> | <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="X Video Downloader — 界面预览" width="780">
</p>

<p align="center">
  <a href="https://github.com/1989Mei/x-video-downloader/releases/latest"><img src="https://img.shields.io/github/v/release/1989Mei/x-video-downloader.svg" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platforms">
  <img src="https://img.shields.io/badge/dependencies-yt--dl%20only-success.svg" alt="Dependencies">
</p>

---

> ## ⚠️ 免责声明
>
> 本工具仅供**个人备份与学习研究**使用。
>
> - 下载内容的版权归原作者及平台所有
> - 请遵守 X（Twitter）的服务条款与您所在地区的法律法规
> - **严禁**将下载内容用于侵犯著作权、商业再分发或任何违法用途
>
> 使用者需自行承担因使用本工具产生的一切后果。作者不对任何滥用行为负责。
> **如果你不确定某个用途是否合规，那就不要做。**

---

## 这是什么

一个跑在**你自己电脑上**的网页工具：粘贴 X（Twitter）的推文链接 → 解析出所有可用画质 → 选一个 → 下载到本地。

不需要登录 X，不需要申请 API，不向任何第三方服务器发送数据。

```
粘贴链接  →  解析画质  →  选一档  →  排队下载  →  打开文件夹
```

## 特点

| | |
|---|---|
| 🎛 **可视化选画质** | 按分辨率自动分组，标注实际体积，并给出推荐档 |
| 🔊 **自动合并音视频** | X 的 HLS 流是纯视频轨，工具会自动补上音轨并合并 |
| ⚡ **并发分片下载** | 默认 4 路并发。实测比单线程快约 60 倍（16 KB/s → 1.1 MB/s） |
| 🍪 **浏览器 Cookie** | 受保护 / 年龄限制的推文也能下载 |
| 📋 **下载队列** | 一次加多个自动排队，随时可取消 |
| 🧹 **目录只留成品** | 每次任务结束自动清理临时分片，下载目录不会被中间文件塞满 |
| 🔄 **一键更新 yt-dlp** | X 的接口改动频繁，保持最新才不会失效 |
| 🌏 **中英双语界面** | 页面右上角一键切换 |
| 🔒 **本地接口有防护** | 随机 token + Origin 校验，防止其它网页偷偷调用你的下载器 |
| 📦 **几乎零依赖** | 后端只用 Python 标准库；唯一第三方依赖是 yt-dlp |

---

## 快速开始

两种用法，挑一种：

### 方式一 · 下载即用（推荐，无需任何环境准备）

到 **[Releases](https://github.com/1989Mei/x-video-downloader/releases/latest)** 下载
`x-video-downloader.exe`，双击运行，浏览器会自动打开。

- ✅ 不需要装 Python
- ✅ 不需要装 yt-dlp（已内置）
- ⚙️ ffmpeg 可选 —— 见下方说明

> ⚠️ **首次运行 Windows 可能拦一下**（程序没有代码签名）：
> 点「**更多信息**」→「**仍要运行**」。
> 杀毒软件误报也是同理 —— 这是 PyInstaller 打包程序的常见现象；
> 源码完全公开，你也可以用 `build_exe.py` 自己构建。

配置文件和下载记录都在 **exe 旁边**，整个文件夹拷走即可（便携模式）。

### 方式二 · 从源码运行（需要 Python 3.9+）

**Windows** — 双击 `run.bat`。脚本会自动找到 Python；只有在完全找不到 yt-dlp 时才会安装它。

**macOS / Linux**

```bash
git clone https://github.com/1989Mei/x-video-downloader.git
cd x-video-downloader
./run.sh
```

也可以直接用 Python 启动：

```bash
pip install -U yt-dlp
python app.py
```

首次运行会生成 `config.json`，并自动打开浏览器。

### 关于 ffmpeg（可选）

ffmpeg 只用来**把视频轨和音频轨合并**。

**没有它程序照样能用** —— 会自动只提供「自带音频」的格式，并把需要合并的格式标灰禁用。
画质一样，只是文件大约 2–4 倍大。**不会下出没声音的视频。**

想用更省空间的格式，装一下即可：

| 平台 | 命令 |
|---|---|
| Windows | `winget install Gyan.FFmpeg` 或 `scoop install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Debian / Ubuntu | `sudo apt install ffmpeg` |

装完重启程序即可识别。

---

## 使用方法

1. **粘贴推文链接**，点「解析」
   （支持 `x.com/...` 和 `twitter.com/...` 两种域名）
2. **选一档画质** —— 带「推荐」标记的是默认建议
3. **需要时选 Cookie** —— 受保护或年龄限制的推文必须选
4. **确认保存目录**（会自动记住，下次不用再填）
5. 点「加入下载队列」

任务会**依次**执行，完成后可以点「打开所在文件夹」直接定位到文件。

---

## 关于画质选项（值得读一下）

X 为同一个视频提供**两套编码**，体积差别很大：

| 类型 | 说明 | 相对体积 |
|---|---|---|
| **HLS** | 自适应码率切片流，压缩效率高 | 小 |
| **HTTP** | 渐进式 MP4，接近原始码率 | 约 **4 倍** |

举例：同一个 720p 画面，HLS 版 1.16 GB，HTTP 版 3.99 GB。

**建议：**

- **访谈、影视、口播类** → 选 **HLS**，画质基本看不出差别，体积省一大半
- **画面里有大量文字、图表，或需要逐帧细看** → 再选 **HTTP**

**推荐档是怎么算的：** 在最高分辨率里，挑总体积不超过 1.5 GB 的那一档。所以短视频会自动推荐 1080p，而 4 小时的长视频会自动降到 720p —— 不用你每次手动算。

---

## 命令行参数

```
python app.py [选项]

  --port N          监听端口（默认 8765，被占用时自动顺延）
  --outdir PATH     下载目录（默认 ~/Downloads）
  --proxy URL       HTTP 代理，例如 http://127.0.0.1:7890（默认自动探测）
  --cookies NAME    复用浏览器 Cookie：chrome / edge / firefox / brave / safari
  --fragments N     并发分片数，1–16（默认 4）
  --no-browser      启动后不自动打开浏览器
  --no-auto-clean   下载结束后保留 .part / .ytdl 临时文件（默认会自动清理）
  --version         显示版本
```

也支持环境变量：`XDL_OUTDIR`、`XDL_PROXY`、`XDL_PORT`、`XDL_COOKIES`、`XDL_FRAGMENTS`、`XDL_OPEN_BROWSER`。

**优先级：** 内置默认值 → `config.json` → 环境变量 → 命令行参数

### 手动用 yt-dlp 做同样的事

这个工具内部就是调用 yt-dlp。如果你想自己敲命令：

```bash
# 1) 看有哪些格式
yt-dlp --proxy http://127.0.0.1:7890 -F "https://x.com/用户/status/1234567890"

# 2) 按格式 ID 下载
yt-dlp --proxy http://127.0.0.1:7890 \
  --concurrent-fragments 4 --fragment-retries 25 --retries 25 \
  -f "hls-506+hls-audio-128000-Audio" \
  --merge-output-format mp4 \
  -o "下载目录/%(uploader_id)s_%(id)s.%(ext)s" \
  "https://x.com/用户/status/1234567890"
```

> ⚠️ **最容易踩的坑**：X 上的 `hls-*` 格式是**纯视频**，必须用 `+` 拼上音频 ID，否则下出来没声音。`http-*` 格式自带音频，直接写 ID 即可。

---

## 配置文件

`config.json`（首次运行自动生成）：

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

| 字段 | 说明 |
|---|---|
| `outdir` | 留空表示使用 `~/Downloads` |
| `proxy` | 留空表示自动探测常见本地代理端口 |
| `cookies_browser` | 留空表示默认不带 Cookie |
| `auto_clean_temp` | 默认 `true`：每次任务结束自动清理临时分片，让目录只剩成品 |

---

## 常见问题

**Q：解析失败 / 一直转圈？**
X 在部分网络环境下无法直连，需要代理。启动日志里会打印探测到的代理；没探测到就用 `--proxy` 手动指定。

**Q：下出来的视频没有声音？**
说明你选的格式是纯视频轨但音频没合并成功。最常见原因是**缺 ffmpeg**，看启动日志里的 `ffmpeg` 那一行。装上 ffmpeg 后重新下载即可。

**Q：提示 "No video could be found"？**
这条推文里没有视频（纯文字或图片）。引用推文、转推有时也会这样。

**Q：受保护 / 年龄限制的推文下不了？**
在「浏览器 Cookie」里选你已登录 X 的那个浏览器。注意下载期间该浏览器最好不要完全退出。

**Q：下载中断了怎么办？**
把同样的任务再加一次就行，会**断点续传**。yt-dlp 保留着已下载的分片，不会从头开始。
⚠️ 不要手动删除下载目录里的 `.part` 和 `Frag*` 文件。

**Q：文件名是怎么定的？**

```
作者ID_媒体ID_画质.ext
```

例如：

```
jpmorgan_2107839924783206400_720p-hls.mp4
jpmorgan_2107839924783206400_1080p-http.mp4
jpmorgan_2107839924783206400_audio.mp4
```

**画质写进文件名**，所以同一部视频的不同画质**不会互相覆盖** ——
720p / 1080p / 仅音频 可以放心各下一遍，互不影响。

**同一个视频、同一个画质重复下载**时，因为文件已经在了，程序会**跳过并明确告诉你**
（显示「同名文件已存在，未重新下载」），而不是静默地假装下载成功。
想重新下就先删掉旧文件。

---

**Q：下载目录里出现了 `.part` 或 `Frag*` 文件？**

正常情况下**不会**。程序在每次任务结束后都会自动清理临时文件，**目录里只会留下成品**。
（注意：下载**失败**时会特意保留临时文件 —— 这样重试才能续传而不是从头开始。）

如果你确实看到了一堆临时文件，两种处理方式：

- 想继续下 → 把同样的链接再加一次，自动续传
- 不想下了 → 点队列上方的「**清理临时文件**」，一键清空

那个按钮会扫描下载目录里的 `*.part`、`*.part-Frag*`、`*.ytdl` 并删除，
**只删临时文件，绝不会碰成品**。

**Q：速度不稳定？**
取决于你的代理带宽。可以用 `--fragments` 调整并发数（默认 4，最大 16）。

**Q：端口被占用？**
程序会自动往后找可用端口，实际地址以启动窗口输出为准。也可以 `--port` 指定。

**Q：为什么本地服务还需要 token？**
防止其它网页偷偷向 `127.0.0.1` 发请求、让你的电脑在不知情的情况下开始下载文件。token 每次启动随机生成，只注入到本页面里。

**Q：支持哪些平台？**
Windows 已充分测试。macOS / Linux 的代码路径已实现（路径、打开文件夹、启动脚本），但**尚未在真机验证** —— 遇到问题欢迎提 Issue。

---

## 项目结构

```
x-video-downloader/
├── app.py              # 入口：HTTP 服务与路由
├── core/
│   ├── config.py       # 配置加载 + 代理探测
│   ├── ytdlp.py        # yt-dlp 定位 / 版本 / 更新 / 解析 / 命令构造
│   ├── tasks.py        # 下载队列与取消
│   └── util.py         # 跨平台小工具
├── web/
│   ├── index.html
│   ├── style.css
│   └── app.js          # 前端逻辑 + 中英双语字典
├── run.bat / run.sh
├── build_exe.py        # PyInstaller 打包脚本（生成单文件 exe）
├── config.example.json
└── requirements.txt
```

设计上刻意保持**无框架、无构建步骤** —— 克隆下来就能跑，也方便你按自己的需求改。

---

## 贡献

欢迎 Issue 和 PR。提交前请确认：

- 不引入新的第三方依赖（除非有充分理由）
- 改动后在 Windows 上实际跑一遍

### 自己打包 exe

```bash
pip install pyinstaller yt-dlp
python build_exe.py
```

产物在 `dist/`。exe 里内置了 Python 运行时和 yt-dlp，所以体积约 17 MB。

---

## License

[MIT](LICENSE) © 2026 1989Mei
