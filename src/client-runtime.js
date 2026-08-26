const PLUGIN_ID = 'dsh-whale-animation';
const STATUS_SELECTOR = '.Md3f7G_turnStatus[role="status"], [class*="_turnStatus"][role="status"]';
const HOST_SELECTOR = '[data-dsh-whale-host="true"]';
const HOST_ATTRIBUTE = 'data-dsh-whale-host';
const STATE_ATTRIBUTE = 'data-dsh-whale-state';
const STATE_KEYS = __WHALE_STATE_KEYS__;
const PLAYLIST = __WHALE_PLAYLIST__;
const DEFAULT_STATE = __WHALE_DEFAULT_STATE__;
const PLAYLIST_INTERVAL_MS = __WHALE_PLAYLIST_INTERVAL_MS__;
const css = __WHALE_CSS__;

const KEYWORD_GROUPS = [
  {
    state: 'alert',
    keywords: ['error', 'failed', 'failure', 'retry', 'retrying', 'exception', '错误', '失败', '重试', '异常'],
  },
  {
    state: 'sonar',
    keywords: ['search', 'searching', 'browse', 'browsing', 'research', 'lookup', 'web', '搜索', '检索', '浏览', '调研'],
  },
  {
    state: 'work',
    keywords: ['tool', 'using tool', 'executing', 'running command', 'shell', 'terminal', 'build', 'test', '工具', '执行', '命令', '构建', '测试'],
  },
  {
    state: 'compose',
    keywords: ['writing', 'generating', 'responding', 'streaming', 'composing', 'drafting', '撰写', '生成', '回答', '输出', '流式'],
  },
  {
    state: 'idle',
    keywords: ['waiting', 'queued', 'queueing', 'paused', 'pending', '等待', '排队', '暂停'],
  },
  {
    state: 'dive',
    keywords: ['thinking', 'reasoning', 'analyzing', 'planning', '思考', '推理', '分析', '规划'],
  },
];

function normalizeText(value) {
  return String(value ?? '').toLocaleLowerCase().replace(/\s+/g, ' ').trim();
}

function resolveWhaleState(text) {
  const normalized = normalizeText(text);
  if (normalized === '') return null;
  for (const group of KEYWORD_GROUPS) {
    if (!STATE_KEYS.includes(group.state)) continue;
    if (group.keywords.some(keyword => normalized.includes(keyword))) return group.state;
  }
  return null;
}

function chooseWhaleState(text, elapsedMs, reducedMotion = false) {
  const explicit = resolveWhaleState(text);
  if (explicit !== null) return explicit;
  if (reducedMotion || PLAYLIST.length === 0) return DEFAULT_STATE;
  const elapsed = Number.isFinite(elapsedMs) ? Math.max(0, elapsedMs) : 0;
  const index = Math.floor(elapsed / PLAYLIST_INTERVAL_MS) % PLAYLIST.length;
  return PLAYLIST[index] ?? DEFAULT_STATE;
}

function removeOwnedDom() {
  const previousStyle = document.querySelector(`style[data-plugin="${PLUGIN_ID}"]`);
  if (previousStyle) previousStyle.remove();
  for (const host of document.querySelectorAll(HOST_SELECTOR)) {
    host.removeAttribute(HOST_ATTRIBUTE);
    host.removeAttribute(STATE_ATTRIBUTE);
  }
}

function apply(ctx) {
  ctx.effect(() => {
    removeOwnedDom();

    const style = document.createElement('style');
    style.dataset.plugin = PLUGIN_ID;
    style.textContent = css;
    document.head.appendChild(style);

    const tracked = new Set();
    const metadata = new WeakMap();
    const motionQuery = typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : { matches: false };
    let disposed = false;
    let scanQueued = false;

    function setState(host, entry, state) {
      const nextState = STATE_KEYS.includes(state) ? state : DEFAULT_STATE;
      if (entry.state === nextState && host.getAttribute(HOST_ATTRIBUTE) === 'true') return;
      entry.state = nextState;
      host.setAttribute(HOST_ATTRIBUTE, 'true');
      host.setAttribute(STATE_ATTRIBUTE, nextState);
    }

    function refreshHost(host, now = Date.now()) {
      const entry = metadata.get(host);
      if (!entry) return;
      const state = chooseWhaleState(host.textContent, now - entry.startedAt, motionQuery.matches);
      setState(host, entry, state);
    }

    function attachHost(host, now = Date.now()) {
      let entry = metadata.get(host);
      if (!entry) {
        entry = { startedAt: now, state: null };
        metadata.set(host, entry);
        tracked.add(host);
      }
      refreshHost(host, now);
    }

    function pruneDisconnected() {
      for (const host of tracked) {
        if (host.isConnected === false) tracked.delete(host);
      }
    }

    function scan() {
      if (disposed) return;
      const now = Date.now();
      for (const host of document.querySelectorAll(STATUS_SELECTOR)) attachHost(host, now);
      pruneDisconnected();
      for (const host of tracked) refreshHost(host, now);
    }

    function scheduleScan() {
      if (scanQueued || disposed) return;
      scanQueued = true;
      const enqueue = typeof queueMicrotask === 'function'
        ? queueMicrotask
        : callback => Promise.resolve().then(callback);
      enqueue(() => {
        scanQueued = false;
        scan();
      });
    }

    const observer = typeof MutationObserver === 'function'
      ? new MutationObserver(scheduleScan)
      : null;
    if (observer && document.documentElement) {
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }

    const interval = setInterval(scan, 1000);
    const onMotionChange = () => scan();
    if (typeof motionQuery.addEventListener === 'function') {
      motionQuery.addEventListener('change', onMotionChange);
    } else if (typeof motionQuery.addListener === 'function') {
      motionQuery.addListener(onMotionChange);
    }

    scan();

    return () => {
      disposed = true;
      clearInterval(interval);
      if (observer) observer.disconnect();
      if (typeof motionQuery.removeEventListener === 'function') {
        motionQuery.removeEventListener('change', onMotionChange);
      } else if (typeof motionQuery.removeListener === 'function') {
        motionQuery.removeListener(onMotionChange);
      }
      for (const host of tracked) {
        if (host.getAttribute(HOST_ATTRIBUTE) === 'true') {
          host.removeAttribute(HOST_ATTRIBUTE);
          host.removeAttribute(STATE_ATTRIBUTE);
        }
      }
      tracked.clear();
      style.remove();
    };
  }, `${PLUGIN_ID}: reactive whale director`);
}

exports.apply = apply;
exports.chooseWhaleState = chooseWhaleState;
exports.name = PLUGIN_ID;
exports.playlist = PLAYLIST;
exports.resolveWhaleState = resolveWhaleState;
exports.statusSelector = STATUS_SELECTOR;
