const PLUGIN_ID = 'dsh-whale-animation';
const STATUS_SELECTOR = '.Md3f7G_turnStatus[role="status"], [class*="_turnStatus"][role="status"]';
const HOST_SELECTOR = '[data-dsh-whale-host="true"]';
const HOST_ATTRIBUTE = 'data-dsh-whale-host';
const STATE_ATTRIBUTE = 'data-dsh-whale-state';
const STATE_KEYS = __WHALE_STATE_KEYS__;
const PLAYLIST = __WHALE_PLAYLIST__;
const DEFAULT_STATE = __WHALE_DEFAULT_STATE__;
const STATE_DURATIONS_MS = __WHALE_STATE_DURATIONS_MS__;
const ANIMATED_ASSETS = __WHALE_ANIMATED_ASSETS__;
const PLAYLIST_DURATION_MS = PLAYLIST.reduce((total, state) => total + STATE_DURATIONS_MS[state], 0);
const css = __WHALE_CSS__;

const EXACT_STATE_ALIASES = new Map([
  ['classic', 'classic'],
  ['original', 'classic'],
  ['经典', 'classic'],
  ['原版', 'classic'],
]);

const KEYWORD_GROUPS = [
  {
    state: 'classic',
    keywords: ['classic whale', 'legacy whale', 'original whale', '经典鲸鱼', '原版鲸鱼', '旧版鲸鱼'],
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
  const exact = EXACT_STATE_ALIASES.get(normalized);
  if (exact && STATE_KEYS.includes(exact)) return exact;
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
  let position = elapsed % PLAYLIST_DURATION_MS;
  for (const state of PLAYLIST) {
    if (position < STATE_DURATIONS_MS[state]) return state;
    position -= STATE_DURATIONS_MS[state];
  }
  return DEFAULT_STATE;
}

function removeOwnedDom() {
  const previousStyle = document.querySelector(`style[data-plugin="${PLUGIN_ID}"]`);
  if (previousStyle) previousStyle.remove();
  for (const host of document.querySelectorAll(HOST_SELECTOR)) {
    host.removeAttribute(HOST_ATTRIBUTE);
    host.removeAttribute(STATE_ATTRIBUTE);
    host.style.removeProperty('--dsh-whale-current-image');
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
    const decodedBlobs = new Map();
    const motionQuery = typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : { matches: false };
    let disposed = false;
    let scanQueued = false;
    let timer = null;

    function releaseImage(host, entry) {
      if (entry.imageUrl?.startsWith('blob:')) URL.revokeObjectURL(entry.imageUrl);
      entry.imageUrl = null;
      host.style.removeProperty('--dsh-whale-current-image');
    }

    function prepareBlob(state) {
      if (!decodedBlobs.has(state)) {
        const encoded = ANIMATED_ASSETS[state].split(',')[1];
        let bytes;
        if (typeof Uint8Array.fromBase64 === 'function') {
          bytes = Uint8Array.fromBase64(encoded);
        } else {
          const binary = atob(encoded);
          bytes = new Uint8Array(binary.length);
          for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
        }
        decodedBlobs.set(state, new Blob([bytes], { type: 'image/webp' }));
      }
      return decodedBlobs.get(state);
    }

    function freshImageUrl(state) {
      if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function' || typeof Blob !== 'function') return ANIMATED_ASSETS[state];
      // Each entry gets a new resource identity. Reusing an animated data URL
      // can inherit another status element's decoder position in Chromium.
      return URL.createObjectURL(prepareBlob(state));
    }

    function setState(host, entry, state) {
      const nextState = STATE_KEYS.includes(state) ? state : DEFAULT_STATE;
      if (entry.state === nextState && entry.reduced === motionQuery.matches && (entry.reduced || entry.imageUrl !== null) && host.getAttribute(HOST_ATTRIBUTE) === 'true') return;
      releaseImage(host, entry);
      entry.state = nextState;
      entry.reduced = motionQuery.matches;
      if (!entry.reduced) {
        entry.imageUrl = freshImageUrl(nextState);
        host.style.setProperty('--dsh-whale-current-image', `url("${entry.imageUrl}")`);
      }
      host.setAttribute(HOST_ATTRIBUTE, 'true');
      host.setAttribute(STATE_ATTRIBUTE, nextState);
    }

    function refreshHost(host, now = Date.now()) {
      const entry = metadata.get(host);
      if (!entry) return;
      if (motionQuery.matches) {
        setState(host, entry, chooseWhaleState(host.textContent, 0, true));
        entry.nextAt = null;
        return;
      }
      if (entry.state === null || entry.nextAt === null) {
        const state = entry.state ?? chooseWhaleState(host.textContent, 0);
        setState(host, entry, state);
        entry.nextAt = now + STATE_DURATIONS_MS[state];
      } else if (now >= entry.nextAt) {
        // A changed status may request another loop, but never interrupts the
        // loop already on screen. The encoded frame durations own this clock.
        const next = resolveWhaleState(host.textContent)
          ?? PLAYLIST[(PLAYLIST.indexOf(entry.state) + 1) % PLAYLIST.length]
          ?? DEFAULT_STATE;
        if (next === entry.state) {
          const duration = STATE_DURATIONS_MS[next];
          entry.nextAt += (Math.floor((now - entry.nextAt) / duration) + 1) * duration;
        } else {
          setState(host, entry, next);
          entry.nextAt = now + STATE_DURATIONS_MS[next];
        }
      }
    }

    function attachHost(host, now = Date.now()) {
      let entry = metadata.get(host);
      if (!entry) {
        entry = { nextAt: null, state: null };
        metadata.set(host, entry);
      }
      tracked.add(host);
      refreshHost(host, now);
    }

    function pruneDisconnected() {
      for (const host of tracked) {
        if (host.isConnected === false) {
          const entry = metadata.get(host);
          releaseImage(host, entry);
          entry.state = null;
          entry.nextAt = null;
          tracked.delete(host);
        }
      }
    }

    function scan() {
      if (disposed || document.hidden) return;
      const now = Date.now();
      for (const host of document.querySelectorAll(STATUS_SELECTOR)) attachHost(host, now);
      pruneDisconnected();
      for (const host of tracked) refreshHost(host, now);
      scheduleNextCycle();
    }

    function scheduleNextCycle() {
      if (timer !== null) clearTimeout(timer);
      timer = null;
      if (disposed || document.hidden) return;
      let nextAt = Infinity;
      for (const host of tracked) {
        const entry = metadata.get(host);
        if (entry && entry.nextAt !== null) nextAt = Math.min(nextAt, entry.nextAt);
      }
      // Modern DSH browsers observe inserted status text without idle polling.
      if (!observer) nextAt = Math.min(nextAt, Date.now() + 1000);
      if (Number.isFinite(nextAt)) timer = setTimeout(scan, Math.max(0, nextAt - Date.now()));
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

    const onVisibilityChange = () => {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
      if (document.hidden) {
        for (const host of tracked) {
          const entry = metadata.get(host);
          releaseImage(host, entry);
          entry.nextAt = null;
        }
      }
      if (!disposed && !document.hidden) {
        if (!motionQuery.matches && typeof Blob === 'function') {
          for (const state of STATE_KEYS) prepareBlob(state);
        }
        scan();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    const onMotionChange = () => scan();
    if (typeof motionQuery.addEventListener === 'function') {
      motionQuery.addEventListener('change', onMotionChange);
    } else if (typeof motionQuery.addListener === 'function') {
      motionQuery.addListener(onMotionChange);
    }

    onVisibilityChange();

    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      if (observer) observer.disconnect();
      if (typeof motionQuery.removeEventListener === 'function') {
        motionQuery.removeEventListener('change', onMotionChange);
      } else if (typeof motionQuery.removeListener === 'function') {
        motionQuery.removeListener(onMotionChange);
      }
      for (const host of tracked) {
        releaseImage(host, metadata.get(host));
        if (host.getAttribute(HOST_ATTRIBUTE) === 'true') {
          host.removeAttribute(HOST_ATTRIBUTE);
          host.removeAttribute(STATE_ATTRIBUTE);
        }
      }
      tracked.clear();
      decodedBlobs.clear();
      style.remove();
    };
  }, `${PLUGIN_ID}: preserved two-loop whale director`);
}

exports.apply = apply;
exports.chooseWhaleState = chooseWhaleState;
exports.name = PLUGIN_ID;
exports.playlist = PLAYLIST;
exports.resolveWhaleState = resolveWhaleState;
exports.statusSelector = STATUS_SELECTOR;
