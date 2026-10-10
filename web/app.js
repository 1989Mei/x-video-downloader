/* x-video-downloader — front-end (vanilla JS, no build step) */
(() => {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* token + api                                                         */
  /* ------------------------------------------------------------------ */
  const TOKEN = (document.querySelector('meta[name="xdl-token"]') || {}).content || '';

  async function api(path, body) {
    const opt = { headers: { 'X-XDL-Token': TOKEN } };
    if (body !== undefined) {
      opt.method = 'POST';
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const res = await fetch(path, opt);
    if (res.status === 403) throw new Error(t('errForbidden'));
    return res.json();
  }

  /* ------------------------------------------------------------------ */
  /* i18n                                                                */
  /* ------------------------------------------------------------------ */
  const I18N = {
    zh: {
      title: 'X 视频下载器',
      subtitle: '粘贴推文链接 → 解析 → 选择画质 → 下载到本地',
      disclaimer: '⚠️ 仅供个人备份 / 学习研究使用。请遵守 X 的服务条款及当地法律，不得用于侵犯著作权或商业再分发。',
      urlLabel: '推文链接',
      urlPlaceholder: 'https://x.com/用户名/status/1234567890',
      parse: '解析',
      parsing: '解析中…',
      chooseQuality: '选择画质',
      cookies: '浏览器 Cookie',
      cookiesOff: '不使用（推荐先试）',
      saveTo: '保存到',
      startDownload: '加入下载队列',
      queue: '下载队列',
      clearDone: '清除已完成',
      queueEmpty: '还没有下载任务',
      checkUpdate: '检查更新',
      updating: '更新中…',
      rec: '推荐',
      efficient: '高效压缩',
      original: '原始码率',
      hasAudio: '自带音频',
      needsAudio: '自动配上 128k 音频',
      audioOnly: '仅音频',
      audioOnlyHint: '适合当播客听',
      author: '作者',
      duration: '时长',
      proxy: '代理',
      cmdEquivalent: '查看等价的命令行写法',
      cancel: '取消',
      openFolder: '打开所在文件夹',
      statusQueued: '排队中',
      statusRunning: '下载中',
      statusMerging: '合并中',
      statusDone: '已完成',
      statusError: '失败',
      statusCanceled: '已取消',
      speed: '速度',
      eta: '剩余',
      parseFailTitle: '解析失败：',
      dlQueued: '已加入队列，开始后会依次下载。',
      errNoUrl: '请先粘贴推文链接',
      errBadUrl: '看起来不像推文链接，格式应为 https://x.com/用户名/status/数字',
      errForbidden: '本地接口校验失败，请刷新页面重试',
      errNoTask: '任务不存在',
      noVideo: '这条推文里没有视频',
      hintNoCookie: '受保护或年龄限制的推文，需要在「浏览器 Cookie」里选择你已登录的浏览器。',
      noFFmpeg: '未检测到 <code>ffmpeg</code> —— 当前只能下载「自带音频」的格式，体积约为高效格式的 2–4 倍。装好 ffmpeg 后重启本程序，即可解锁更省空间的格式。',
      needFFmpeg: '需 ffmpeg',
      needFFmpegTip: '这个格式是纯视频轨，需要 ffmpeg 合并音轨；当前没有 ffmpeg，下出来会没有声音',
      updateBundled: '当前用的是程序内置的 yt-dlp，无法在线更新。请到 Releases 页面下载最新版程序。',
      updateDone: '已是最新版本',
      updateOk: '更新完成',
      updateFail: '更新失败',
    },
    en: {
      title: 'X Video Downloader',
      subtitle: 'Paste a post link → parse → pick a quality → download',
      disclaimer: '⚠️ For personal backup / research use only. Respect X\'s Terms of Service and your local laws. Do not use this to infringe copyright or redistribute commercially.',
      urlLabel: 'Post URL',
      urlPlaceholder: 'https://x.com/username/status/1234567890',
      parse: 'Parse',
      parsing: 'Parsing…',
      chooseQuality: 'Choose a quality',
      cookies: 'Browser cookies',
      cookiesOff: 'None (try this first)',
      saveTo: 'Save to',
      startDownload: 'Add to queue',
      queue: 'Downloads',
      clearDone: 'Clear finished',
      queueEmpty: 'No downloads yet',
      checkUpdate: 'Check for updates',
      updating: 'Updating…',
      rec: 'Best',
      efficient: 'efficient',
      original: 'original bitrate',
      hasAudio: 'audio included',
      needsAudio: 'adds 128k audio track',
      audioOnly: 'Audio only',
      audioOnlyHint: 'handy as a podcast',
      author: 'By',
      duration: 'Length',
      proxy: 'Proxy',
      cmdEquivalent: 'Show the equivalent command line',
      cancel: 'Cancel',
      openFolder: 'Open containing folder',
      statusQueued: 'Queued',
      statusRunning: 'Downloading',
      statusMerging: 'Merging',
      statusDone: 'Done',
      statusError: 'Failed',
      statusCanceled: 'Canceled',
      speed: 'Speed',
      eta: 'ETA',
      parseFailTitle: 'Could not parse: ',
      dlQueued: 'Added to the queue. Downloads run one at a time.',
      errNoUrl: 'Please paste a post URL first',
      errBadUrl: 'That does not look like a post URL. Expected https://x.com/<user>/status/<id>',
      errForbidden: 'Local request rejected — please refresh the page',
      errNoTask: 'Task not found',
      noVideo: 'This post contains no video',
      hintNoCookie: 'For protected or age-restricted posts, pick the browser you are logged into under "Browser cookies".',
      noFFmpeg: 'No <code>ffmpeg</code> found — for now only formats that already carry audio can be used, and those are roughly 2–4× larger. Install ffmpeg and restart the app to unlock the more efficient formats.',
      needFFmpeg: 'needs ffmpeg',
      needFFmpegTip: 'This is a video-only stream and needs ffmpeg to merge the audio track; without ffmpeg the result would have no sound',
      updateBundled: 'This build uses the yt-dlp bundled inside the app and cannot self-update. Grab the latest program from the Releases page.',
      updateDone: 'Already up to date',
      updateOk: 'Updated',
      updateFail: 'Update failed',
    },
  };

  let lang = localStorage.getItem('xdl.lang')
    || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en');
  if (!I18N[lang]) lang = 'en';

  function t(key) {
    return (I18N[lang] && I18N[lang][key]) || (I18N.en[key] || key);
  }

  function applyI18n() {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
    document.querySelectorAll('[data-i18n-ph]').forEach(n => { n.placeholder = t(n.dataset.i18nPh); });
    document.title = t('title');
    document.getElementById('btnLang').textContent = lang === 'zh' ? 'EN' : '中文';
    if (INFO) renderQuality(INFO);
    renderTasks(LAST_TASKS);
    if (!LAST_TASKS.length) showEmptyQueue();
    renderEnvNotice();
  }

  /* Environment warnings (e.g. ffmpeg missing) */
  function renderEnvNotice() {
    const n = $('#envNotice');
    if (!META) { n.hidden = true; return; }
    const parts = [];
    if (!META.ffmpeg) parts.push(t('noFFmpeg'));
    if (!parts.length) { n.hidden = true; return; }
    n.innerHTML = parts.join('<br>');   // only our own i18n strings, no user data
    n.hidden = false;
  }

  /* ------------------------------------------------------------------ */
  /* helpers                                                             */
  /* ------------------------------------------------------------------ */
  const $ = s => document.querySelector(s);

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function size(bytes) {
    const n = Number(bytes);
    if (!n || n <= 0) return '?';
    const u = [['GB', 1024 ** 3], ['MB', 1024 ** 2], ['KB', 1024]];
    for (const [name, div] of u) {
      if (n >= div) return (n / div).toFixed(n / div >= 100 ? 0 : 2) + ' ' + name;
    }
    return n + ' B';
  }

  function dur(sec) {
    const n = Math.round(Number(sec) || 0);
    if (n <= 0) return '?';
    const h = Math.floor(n / 3600), m = Math.floor((n % 3600) / 60), s = n % 60;
    if (h) return lang === 'zh' ? `${h} 小时 ${m} 分` : `${h}h ${m}m`;
    if (m) return lang === 'zh' ? `${m} 分 ${s} 秒` : `${m}m ${s}s`;
    return `${s}s`;
  }

  function say(node, text, kind) {
    if (!text) { node.className = 'msg'; node.textContent = ''; return; }
    node.className = 'msg on ' + (kind || 'info');
    node.textContent = text;
  }

  /* ------------------------------------------------------------------ */
  /* settings persistence                                                */
  /* ------------------------------------------------------------------ */
  const store = {
    get outdir() { return localStorage.getItem('xdl.outdir') || ''; },
    set outdir(v) { localStorage.setItem('xdl.outdir', v || ''); },
    get cookies() { return localStorage.getItem('xdl.cookies') || ''; },
    set cookies(v) { localStorage.setItem('xdl.cookies', v || ''); },
  };

  /* ------------------------------------------------------------------ */
  /* state                                                               */
  /* ------------------------------------------------------------------ */
  let INFO = null;
  let META = null;
  let LAST_TASKS = [];
  let pollTimer = null;

  /* ------------------------------------------------------------------ */
  /* boot                                                                */
  /* ------------------------------------------------------------------ */
  async function boot() {
    applyI18n();

    try {
      META = await api('/api/meta');
    } catch (e) { /* ignore; UI still usable */ }

    if (META) {
      $('#verBox').textContent = 'yt-dlp ' + (META.ytdlpVersion || '?');
      $('#verBox').title = 'yt-dlp ' + (META.ytdlpVersion || '?')
        + (META.ytdlpSource ? ' · ' + META.ytdlpSource : '')
        + (META.ffmpeg ? '' : ' · ffmpeg NOT found');
      if (!META.ffmpeg) $('#verBox').style.color = 'var(--er)';
    }
    renderEnvNotice();

    $('#outdir').value = store.outdir || (META ? META.outdir : '');
    $('#cookies').value = store.cookies || (META ? META.cookies : '') || '';

    await refreshTasks();
  }

  /* ------------------------------------------------------------------ */
  /* parse                                                              */
  /* ------------------------------------------------------------------ */
  $('#btnParse').addEventListener('click', doParse);
  $('#url').addEventListener('keydown', e => { if (e.key === 'Enter') doParse(); });

  async function doParse() {
    const url = $('#url').value.trim();
    if (!url) { say($('#parseMsg'), t('errNoUrl'), 'err'); return; }

    const btn = $('#btnParse');
    btn.disabled = true;
    btn.textContent = t('parsing');
    say($('#parseMsg'), t('parsing'), 'info');
    $('#infoCard').hidden = true;
    $('#qualityCard').hidden = true;
    $('#cmdBox').hidden = true;

    try {
      const d = await api('/api/parse', {
        url,
        cookies: $('#cookies').value || '',
      });

      if (!d.ok) {
        let msg = t('parseFailTitle') + (d.detail || d.code || '');
        if (/No video could be found/i.test(d.detail || '')) msg = t('noVideo');
        else if (/protected|not authorized|age/i.test(d.detail || '')) msg = t('hintNoCookie');
        say($('#parseMsg'), msg, 'err');
        return;
      }

      INFO = d;
      say($('#parseMsg'), '');
      renderInfo(d);
      renderQuality(d);
      $('#infoCard').hidden = false;
      $('#qualityCard').hidden = false;
    } catch (e) {
      say($('#parseMsg'), String(e.message || e), 'err');
    } finally {
      btn.disabled = false;
      btn.textContent = t('parse');
    }
  }

  function renderInfo(d) {
    const thumb = $('#thumb');
    if (d.thumbnail) { thumb.src = d.thumbnail; thumb.style.display = ''; }
    else { thumb.style.display = 'none'; }
    $('#vtitle').textContent = d.title;
    $('#vsub').innerHTML =
      `<span>${esc(t('author'))} <b>${esc(d.uploader || d.uploaderId)}</b></span>` +
      `<span>${esc(t('duration'))} <b>${esc(dur(d.duration))}</b></span>` +
      `<span>${esc(t('proxy'))} <b>${esc((META && META.proxy) || '—')}</b></span>`;
  }

  function renderQuality(d) {
    const box = $('#groups');
    const picked = (box.querySelector('input[name=fmt]:checked') || {}).value;
    box.innerHTML = '';

    d.groups.forEach(g => {
      const wrap = document.createElement('div');
      wrap.className = 'group';

      const head = document.createElement('div');
      head.className = 'ghead';
      head.innerHTML = `<span>${g.height}p</span>` +
        `<span class="dim">${g.width ? g.width + '×' + g.height : ''}</span>`;
      wrap.appendChild(head);

      g.options.forEach(o => {
        const locked = o.needsFFmpeg === true;   // needs ffmpeg, which is missing
        const lab = document.createElement('label');
        lab.className = 'opt' + (locked ? ' locked' : '');
        if (locked) lab.title = t('needFFmpegTip');
        const checked = (picked ? o.id === picked : o.id === d.recommended) ? ' checked' : '';
        const badge = (o.id === d.recommended && !locked)
          ? `<span class="badge">${esc(t('rec'))}</span>` : '';
        const warn = locked ? `<span class="warnbadge">${esc(t('needFFmpeg'))}</span>` : '';
        lab.innerHTML =
          `<input type="radio" name="fmt" value="${esc(o.id)}"` +
          ` data-needs="${o.needsAudio ? 1 : 0}" data-audio="${esc(o.audioId || '')}"` +
          `${locked ? ' disabled' : ''}${checked}>` +
          `<span class="proto">${esc(o.protocol)} · ${esc(o.efficient ? t('efficient') : t('original'))}` +
          `<small>${esc(o.needsAudio ? t('needsAudio') : t('hasAudio'))}</small></span>` +
          `<span class="size">${esc(size(o.size))}</span>${warn}${badge}`;
        wrap.appendChild(lab);
      });
      box.appendChild(wrap);
    });

    if (d.audioOnly && d.audioOnly.id) {
      const wrap = document.createElement('div');
      wrap.className = 'group';
      wrap.innerHTML = `<div class="ghead"><span>${esc(t('audioOnly'))}</span>` +
        `<span class="dim">128 kbps</span></div>`;
      const lab = document.createElement('label');
      lab.className = 'opt';
      lab.innerHTML =
        `<input type="radio" name="fmt" value="${esc(d.audioOnly.id)}" data-needs="0" data-audio="">` +
        `<span class="proto">${esc(t('audioOnly'))}<small>${esc(t('audioOnlyHint'))}</small></span>` +
        `<span class="size">${esc(size(d.audioOnly.size))}</span>`;
      wrap.appendChild(lab);
      box.appendChild(wrap);
    }
  }

  /* ------------------------------------------------------------------ */
  /* download                                                            */
  /* ------------------------------------------------------------------ */
  $('#btnDownload').addEventListener('click', startDownload);

  async function startDownload() {
    const picked = document.querySelector('input[name=fmt]:checked');
    if (!picked || !INFO) return;

    const outdir = $('#outdir').value.trim();
    const cookies = $('#cookies').value || '';
    store.outdir = outdir;
    store.cookies = cookies;

    const payload = {
      url: INFO.url,
      title: INFO.title,
      formatId: picked.value,
      needsAudio: picked.dataset.needs === '1',
      audioId: picked.dataset.audio || null,
      outdir,
    };

    try {
      const d = await api('/api/download', payload);
      if (!d.ok) { say($('#dlMsg'), d.code || 'error', 'err'); return; }
      say($('#dlMsg'), t('dlQueued'), 'info');
      $('#cmdBox').hidden = false;
      $('#cmdText').textContent = equivalentCmd(picked.value, payload);
      await refreshTasks();
    } catch (e) {
      say($('#dlMsg'), String(e.message || e), 'err');
    }
  }

  function equivalentCmd(fmtId, p) {
    const sel = (p.needsAudio && p.audioId) ? `${fmtId}+${p.audioId}` : fmtId;
    const proxy = (META && META.proxy) || 'http://127.0.0.1:7890';
    const ck = $('#cookies').value;
    const cookieFlag = ck ? ` --cookies-from-browser ${ck}` : '';
    const out = (p.outdir || '.').replace(/[\\/]+$/, '');
    return `yt-dlp --proxy ${proxy}${cookieFlag} \\\n` +
      `  --concurrent-fragments 4 --fragment-retries 25 --retries 25 \\\n` +
      `  -f "${sel}" --merge-output-format mp4 \\\n` +
      `  -o "${out}/%(uploader_id)s_%(id)s.%(ext)s" \\\n` +
      `  "${p.url}"`;
  }

  /* ------------------------------------------------------------------ */
  /* task list                                                           */
  /* ------------------------------------------------------------------ */
  $('#btnClear').addEventListener('click', async () => {
    try { await api('/api/clear', {}); } catch (e) { /* ignore */ }
    await refreshTasks();
  });

  function showEmptyQueue() {
    const box = $('#tasks');
    if (!LAST_TASKS.length) {
      box.innerHTML = `<div class="empty">${esc(t('queueEmpty'))}</div>`;
    }
  }

  function stageKey(task) {
    if (task.status === 'done') return 'statusDone';
    if (task.status === 'error') return 'statusError';
    if (task.status === 'canceled') return 'statusCanceled';
    if (task.stage === 'merging') return 'statusMerging';
    if (task.status === 'queued') return 'statusQueued';
    return 'statusRunning';
  }

  function renderTasks(tasks) {
    LAST_TASKS = tasks || [];
    const box = $('#tasks');

    if (!LAST_TASKS.length) {
      box.innerHTML = `<div class="empty">${esc(t('queueEmpty'))}</div>`;
      return;
    }

    box.innerHTML = '';
    LAST_TASKS.forEach(task => {
      const chip = task.status === 'running' && task.stage === 'merging'
        ? 'running' : task.status;
      const pct = task.status === 'done' ? 100
        : parseFloat(String(task.percent || '0').replace('%', '')) || 0;

      const el = document.createElement('div');
      el.className = 'task';

      let meta = '';
      if (task.status === 'running') {
        if (task.speed) meta += `<span>${esc(t('speed'))} ${esc(task.speed)}</span>`;
        if (task.eta) meta += `<span>${esc(t('eta'))} ${esc(task.eta)}</span>`;
      }
      if (task.fileSize) meta += `<span>${esc(task.fileSize)}</span>`;
      if (task.status === 'error' && task.error) {
        meta += `<span class="err">${esc(String(task.error).slice(0, 220))}</span>`;
      }

      let acts = '';
      if (task.status === 'queued' || task.status === 'running') {
        acts += `<button class="sm danger" data-act="cancel" data-id="${task.id}">${esc(t('cancel'))}</button>`;
      }
      if (task.status === 'done' && task.file) {
        acts += `<button class="sm" data-act="open" data-path="${esc(task.file)}">${esc(t('openFolder'))}</button>`;
      }

      el.innerHTML =
        `<div class="thead">` +
        `<div class="ttitle">${esc(task.title || task.url)}</div>` +
        `<span class="chip ${chip}">${esc(t(stageKey(task)))}</span>` +
        `</div>` +
        `<div class="bar ${task.status}"><i style="width:${Math.max(0, Math.min(100, pct))}%"></i></div>` +
        (meta ? `<div class="tmeta">${meta}</div>` : '') +
        (task.file && task.status === 'done' ? `<div class="tfile">${esc(task.file)}</div>` : '') +
        (acts ? `<div class="tacts">${acts}</div>` : '');

      box.appendChild(el);
    });
  }

  $('#tasks').addEventListener('click', async e => {
    const btn = e.target.closest('button[data-act]');
    if (!btn) return;
    if (btn.dataset.act === 'cancel') {
      btn.disabled = true;
      try { await api('/api/cancel', { taskId: btn.dataset.id }); } catch (err) { /* ignore */ }
      await refreshTasks();
    } else if (btn.dataset.act === 'open') {
      try { await api('/api/open', { path: btn.dataset.path }); } catch (err) { /* ignore */ }
    }
  });

  async function refreshTasks() {
    try {
      const d = await api('/api/tasks');
      if (d.ok) renderTasks(d.tasks);
    } catch (e) { /* ignore */ }

    const busy = LAST_TASKS.some(x => x.status === 'queued' || x.status === 'running');
    if (busy && !pollTimer) {
      pollTimer = setInterval(refreshTasks, 1200);
    } else if (!busy && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  /* ------------------------------------------------------------------ */
  /* yt-dlp update                                                       */
  /* ------------------------------------------------------------------ */
  $('#btnUpdate').addEventListener('click', async () => {
    const btn = $('#btnUpdate');
    btn.disabled = true;
    const old = btn.textContent;
    btn.textContent = t('updating');
    try {
      const d = await api('/api/update', {});
      $('#verBox').textContent = 'yt-dlp ' + (d.version || '?');
      if (d.code === 'BUNDLED') {
        say($('#parseMsg'), t('updateBundled'), 'info');
      } else {
        say($('#parseMsg'), d.ok ? t('updateOk') : t('updateFail'), d.ok ? 'info' : 'err');
      }
    } catch (e) {
      say($('#parseMsg'), String(e.message || e), 'err');
    } finally {
      btn.disabled = false;
      btn.textContent = old;
    }
  });

  /* ------------------------------------------------------------------ */
  /* language                                                            */
  /* ------------------------------------------------------------------ */
  $('#btnLang').addEventListener('click', () => {
    lang = lang === 'zh' ? 'en' : 'zh';
    localStorage.setItem('xdl.lang', lang);
    applyI18n();
  });

  boot();
})();
