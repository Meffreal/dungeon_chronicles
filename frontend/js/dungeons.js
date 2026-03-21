// ── DUNGEONS ───────────────────────────────────────────────────────────────
console.log('[Dungeons.js] Script loaded');

function _hexToRgb(hex) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return r + ',' + g + ',' + b;
}

const MAP_POSITIONS = {
  'tomb_of_forgotten': { left: '23.75%', top: '66%' },
  'fiery_depths':      { left: '75%',    top: '62%' },
  'citadel_of_chaos':  { left: '50%',    top: '24%' },
};

let _unlockedAttunements = new Set();

// Načítáno z API (/dungeon/config) — viz loadDungeons()
let DUNGEON_DATA = [];

async function loadDungeons() {
  const el = document.getElementById('dungeon-content');
  if (!el) {
    console.error('[Dungeons] dungeon-content element not found');
    return;
  }
  showLoading('dungeon-content');
  try {
    const [dungeonCfg, data, statusData] = await Promise.all([
      api('GET', '/dungeon/config'),
      api('GET', '/attunement/progress'),
      api('GET', '/dungeon/status'),
    ]);
    DUNGEON_DATA = Array.isArray(dungeonCfg) ? dungeonCfg : [];

    // Pokud hráč má aktivní nebo nedokončený run, zobraz run UI místo mapy
    const run = statusData?.run;
    if (run && run.status === 'active') {
      if (typeof renderActiveDungeon === 'function') renderActiveDungeon(run, null);
      return;
    }
    if (run && !run.reward_claimed && (run.status === 'completed' || (run.status === 'failed' && (run.reward_xp > 0 || run.reward_gold > 0)))) {
      if (typeof renderDungeonReady === 'function') renderDungeonReady(run);
      return;
    }

    renderDungeons(data);
  } catch(e) {
    console.error('[Dungeons] Error loading:', e);
    const msg = (e && e.message) ? String(e.message) : String(e);
    if (el) el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Chyba načítání</div><div class="empty-state-hint">${msg.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div></div>`;
  }
}

function renderDungeons(data) {
  const el = document.getElementById('dungeon-content');
  if (!el) return;

  _unlockedAttunements = new Set(data.unlocked_attunements || []);
  const unlockedCount = _unlockedAttunements.size;

  el.innerHTML = `
    <div class="dng-map-container">
      ${_buildMapSvg()}
      <div class="dng-map-hud">
        <span class="dng-map-hud-stat"><span class="c-purple">${unlockedCount}</span> odemčeno</span>
        <span class="dng-map-hud-sep">·</span>
        <span class="dng-map-hud-stat">${DUNGEON_DATA.length} celkem</span>
      </div>
      <div class="dng-map-nodes">
        ${DUNGEON_DATA.map(d => _renderMapNode(d, _unlockedAttunements.has(d.attunement_id))).join('')}
      </div>
      <div class="dng-map-panel" id="dng-map-panel">
        <div class="dng-map-panel-inner" id="dng-map-panel-inner"></div>
      </div>
    </div>`;
}

function _buildMapSvg() {
  return `<svg class="dng-map-svg" viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
  <defs>
    <radialGradient id="gTomb" cx="23.75%" cy="66%" r="30%">
      <stop offset="0%" stop-color="#9b59b6" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#9b59b6" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gFire" cx="75%" cy="62%" r="30%">
      <stop offset="0%" stop-color="#e67e22" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#e67e22" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gChaos" cx="50%" cy="24%" r="25%">
      <stop offset="0%" stop-color="#1abc9c" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#1abc9c" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gVig" cx="50%" cy="50%" r="70%">
      <stop offset="50%" stop-color="#06040f" stop-opacity="0"/>
      <stop offset="100%" stop-color="#06040f" stop-opacity="0.75"/>
    </radialGradient>
  </defs>

  <!-- Vrstva 1: Temné pozadí -->
  <rect width="800" height="500" fill="#06040f"/>

  <!-- Vrstva 2: Biome záře -->
  <rect width="800" height="500" fill="url(#gTomb)"/>
  <rect width="800" height="500" fill="url(#gFire)"/>
  <rect width="800" height="500" fill="url(#gChaos)"/>

  <!-- Vrstva 3: Terén — Hrobka -->
  <ellipse cx="190" cy="360" rx="110" ry="45" fill="#0d0518" opacity="0.8"/>
  <rect x="148" y="315" width="11" height="22" rx="5" fill="#1a0d2e" opacity="0.85"/>
  <rect x="167" y="308" width="13" height="26" rx="6" fill="#1f1035" opacity="0.85"/>
  <rect x="188" y="320" width="10" height="20" rx="5" fill="#1a0d2e" opacity="0.85"/>
  <rect x="206" y="312" width="14" height="24" rx="6" fill="#1f1035" opacity="0.85"/>
  <rect x="225" y="318" width="11" height="20" rx="5" fill="#1a0d2e" opacity="0.85"/>
  <line x1="155" y1="315" x2="152" y2="285" stroke="#150a25" stroke-width="3" opacity="0.7"/>
  <line x1="152" y1="295" x2="142" y2="280" stroke="#150a25" stroke-width="2" opacity="0.5"/>
  <line x1="152" y1="295" x2="160" y2="278" stroke="#150a25" stroke-width="2" opacity="0.5"/>
  <line x1="230" y1="318" x2="235" y2="288" stroke="#150a25" stroke-width="3" opacity="0.6"/>
  <line x1="235" y1="300" x2="245" y2="290" stroke="#150a25" stroke-width="2" opacity="0.4"/>

  <!-- Vrstva 3: Terén — Sopka -->
  <polygon points="600,460 545,295 655,295" fill="#120600" opacity="0.9"/>
  <polygon points="600,460 548,305 652,305" fill="#1a0a00" opacity="0.7"/>
  <ellipse cx="600" cy="295" rx="20" ry="8" fill="#e67e22" opacity="0.35"/>
  <path d="M590,310 Q575,340 565,380 Q560,400 570,420" fill="none" stroke="#c0540a" stroke-width="3" opacity="0.3"/>
  <path d="M610,310 Q625,345 635,385 Q640,405 630,430" fill="none" stroke="#c0540a" stroke-width="3" opacity="0.3"/>
  <ellipse cx="600" cy="450" rx="90" ry="25" fill="#0e0400" opacity="0.8"/>

  <!-- Vrstva 3: Terén — Citadela -->
  <ellipse cx="400" cy="120" rx="55" ry="28" fill="none" stroke="#1abc9c" stroke-width="1.5" opacity="0.25"/>
  <ellipse cx="400" cy="120" rx="40" ry="20" fill="none" stroke="#1abc9c" stroke-width="1" opacity="0.35"/>
  <ellipse cx="400" cy="120" rx="24" ry="12" fill="#0a2520" opacity="0.5"/>
  <path d="M360,95 L345,75 L355,85 L340,68" fill="none" stroke="#1abc9c" stroke-width="1" opacity="0.35"/>
  <path d="M440,98 L458,78 L448,88 L462,70" fill="none" stroke="#1abc9c" stroke-width="1" opacity="0.35"/>
  <path d="M398,168 L390,188 L395,178 L386,196" fill="none" stroke="#1abc9c" stroke-width="1" opacity="0.3"/>
  <rect x="355" y="80" width="8" height="6" rx="2" fill="#0d201c" opacity="0.7" transform="rotate(-15,359,83)"/>
  <rect x="435" y="85" width="10" height="7" rx="2" fill="#0d201c" opacity="0.7" transform="rotate(20,440,88)"/>

  <!-- Vrstva 4: Cesta mezi dungeony -->
  <path d="M190,330 Q280,270 400,220 Q480,185 600,310"
        fill="none" stroke="#4a3810" stroke-width="3"
        stroke-dasharray="8,5" opacity="0.5"/>
  <path d="M190,330 Q280,270 400,220 Q480,185 600,310"
        fill="none" stroke="#c8a020" stroke-width="1.5"
        stroke-dasharray="8,5" opacity="0.2"/>

  <!-- Vrstva 5: Hvězdy -->
  <circle cx="50" cy="30" r="1" fill="#fff" opacity="0.4"/>
  <circle cx="120" cy="60" r="1.2" fill="#fff" opacity="0.3"/>
  <circle cx="200" cy="20" r="0.8" fill="#fff" opacity="0.5"/>
  <circle cx="300" cy="45" r="1" fill="#fff" opacity="0.35"/>
  <circle cx="450" cy="25" r="1.2" fill="#fff" opacity="0.4"/>
  <circle cx="550" cy="50" r="0.8" fill="#fff" opacity="0.3"/>
  <circle cx="650" cy="30" r="1" fill="#fff" opacity="0.45"/>
  <circle cx="740" cy="55" r="1.2" fill="#fff" opacity="0.3"/>
  <circle cx="780" cy="20" r="0.8" fill="#fff" opacity="0.4"/>
  <circle cx="80" cy="140" r="0.8" fill="#fff" opacity="0.25"/>
  <circle cx="700" cy="100" r="1" fill="#fff" opacity="0.3"/>
  <circle cx="760" cy="160" r="0.8" fill="#fff" opacity="0.25"/>

  <!-- Vrstva 6: Vignette -->
  <rect width="800" height="500" fill="url(#gVig)"/>

  <!-- Vrstva 7: Ground glows -->
  <ellipse cx="190" cy="345" rx="45" ry="15" fill="#9b59b6" opacity="0.12"/>
  <ellipse cx="600" cy="320" rx="45" ry="15" fill="#e67e22" opacity="0.12"/>
  <ellipse cx="400" cy="130" rx="35" ry="12" fill="#1abc9c" opacity="0.10"/>
</svg>`;
}

function _renderMapNode(d, isUnlocked) {
  const pos = MAP_POSITIONS[d.dungeon_key] || { left: '50%', top: '50%' };
  const lockedCls = isUnlocked ? '' : 'locked';
  const clickHandler = isUnlocked
    ? `onclick="openDngDetail('${d.dungeon_key}')"`
    : `onclick="openDngDetail('${d.dungeon_key}', true)"`;

  return `
    <div class="dng-map-node ${lockedCls}" style="left:${pos.left};top:${pos.top}" ${clickHandler}>
      <div class="dng-map-node-ring" style="--nc:${d.color};border-color:${d.color}">
        <span class="dng-map-node-icon">${isUnlocked ? d.icon : '🔒'}</span>
        <div class="dng-map-node-pulse" style="--nc:${d.color}"></div>
      </div>
      <div class="dng-map-node-label" style="${isUnlocked ? 'color:#fff' : 'color:rgba(255,255,255,.4)'}">${esc(d.name)}</div>
      ${isUnlocked ? `<div class="dng-map-node-status">⚔ Vstoupit</div>` : `<div class="dng-map-node-status locked-lbl">🔒 Attunement</div>`}
    </div>`;
}

function openDngDetail(key, isLocked) {
  const d = DUNGEON_DATA.find(x => x.dungeon_key === key);
  if (!d) return;
  const panel = document.getElementById('dng-map-panel');
  const inner = document.getElementById('dng-map-panel-inner');
  if (!panel || !inner) return;

  const unlocked = !isLocked;
  const rgb = _hexToRgb(d.color);

  inner.innerHTML = `
    <div class="dng-detail-banner" style="background:linear-gradient(135deg,${d.bg || 'rgba(0,0,0,.5)'},transparent);border-bottom:1px solid ${d.color}33">
      <div class="dng-detail-icon">${unlocked ? d.icon : '🔒'}</div>
      <div class="dng-detail-meta">
        <div class="dng-detail-sub" style="color:${d.color}">${esc(d.subtitle)}</div>
        <div class="dng-detail-title">${esc(d.name)}</div>
        <span class="dbadge ${d.diff_class}">${esc(d.difficulty)}</span>
      </div>
      <button class="dng-map-panel-close" onclick="closeDngDetail()">✕</button>
    </div>
    <div class="dng-detail-body">
      <p class="dng-desc">${esc(d.desc)}</p>
      <div class="dng-flavor" style="border-left-color:${d.color}66">${esc(d.flavor)}</div>
      <div class="dng-boss-panel" style="border-color:${d.color}33;background:linear-gradient(135deg,rgba(0,0,0,.35),${d.color}08)">
        <div class="dng-boss-icon">${unlocked ? d.boss_icon : '❓'}</div>
        <div class="dng-boss-info">
          <div class="dng-boss-label">Final Boss</div>
          <div class="dng-boss-name">${unlocked ? esc(d.boss_name) : '???'}</div>
        </div>
        <div class="dng-boss-glow" style="background:radial-gradient(circle at right,${d.color}22,transparent 70%)"></div>
      </div>
      <div class="dng-info-grid" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
        <div class="dng-info-card"><span class="dng-info-icon">⚔️</span><span class="dng-info-val">Lv. ${d.min_level}+</span><span class="dng-info-lbl">Min. level</span></div>
        <div class="dng-info-card"><span class="dng-info-icon">🏰</span><span class="dng-info-val">${d.floors}</span><span class="dng-info-lbl">Pater</span></div>
      </div>
      ${unlocked ? `
        <div class="dng-rewards-wrap">
          <div class="dng-rewards-title">🎁 Odměny</div>
          <div class="dng-rewards-list">${d.rewards.map(r => `<span class="dng-reward-chip" style="border-color:${d.color}55;color:${d.color}">${esc(r)}</span>`).join('')}</div>
        </div>
        <button class="dng-enter-btn" style="--dc-r:${rgb.split(',')[0]};--dc-g:${rgb.split(',')[1]};--dc-b:${rgb.split(',')[2]}" onclick="closeDngDetail();enterDungeonRun('${d.dungeon_key}', this)">⚔ Vstoupit do dungeonu</button>
      ` : `
        <div class="dng-locked-tease">
          <div class="dng-locked-boss-silhouette">${d.boss_icon}</div>
          <div class="dng-locked-tease-info">
            <div class="dng-locked-tease-boss">Hlídač: <strong>${esc(d.boss_name)}</strong></div>
            <div class="dng-locked-tease-req">
              <span class="dng-req-chain">${d.attunement_badge} ${esc(d.attunement_name)}</span>
              <span class="dng-locked-tease-hint">— pro vstup potřebuješ tento attunement</span>
            </div>
          </div>
        </div>
        <button class="dng-att-btn" onclick="closeDngDetail();showPage('attunement')">🔑 Jít na Attunement</button>
      `}
    </div>`;

  panel.classList.add('open');
}

function closeDngDetail() {
  const panel = document.getElementById('dng-map-panel');
  if (panel) panel.classList.remove('open');
}

async function enterDungeonRun(dungeonKey, btnEl) {
  const btn = btnEl instanceof HTMLElement ? btnEl : null;
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Vstupuji...'; }
  try {
    const result = await api('POST', '/dungeon/enter', { dungeon_key: dungeonKey });
    if (typeof _showStageReplay === 'function') {
      _showStageReplay(result, 1);
    } else {
      toast('🏰 Dungeon zahájen!', 's', 3000);
      if (typeof loadDungeonData === 'function') loadDungeonData();
    }
  } catch(e) {
    toast(e.message || 'Vstup do dungeonu selhal.', 'e');
    if (btn) { btn.disabled = false; btn.textContent = '⚔️ Vstoupit'; }
  }
}
