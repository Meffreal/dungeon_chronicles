// ── DUNGEONS ───────────────────────────────────────────────────────────────
console.log('[Dungeons.js] Script loaded');

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

    // Pokud hráč má aktivní nebo nedokončený run, zobraz run UI místo roadmapy
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
  
  try {
    const unlocked = new Set(data.unlocked_attunements || []);
    const unlockedCount = unlocked.size;

    el.innerHTML = '<div class="dng-hero"><div class="dng-hero-runes" aria-hidden="true"><span style="left:5%;animation-delay:0s">᛭</span><span style="left:20%;animation-delay:2s">ᚱ</span><span style="left:50%;animation-delay:1s">☽</span><span style="left:75%;animation-delay:3s">ᛟ</span><span style="left:90%;animation-delay:1.5s">⚔</span></div><div class="dng-hero-inner"><div class="dng-hero-icon">🗺️</div><div class="dng-hero-title">Mapa Dungeonů</div><div class="dng-hero-sub">Každý dungeon je světem sám pro sebe. Pro vstup potřebuješ příslušný <em>Attunement</em>.</div><div class="dng-hero-stats"><div class="dng-hstat"><span class="dng-hstat-v c-purple">' + unlockedCount + '</span><span class="dng-hstat-l">Odemčeno</span></div><div class="dng-hstat-sep"></div><div class="dng-hstat"><span class="dng-hstat-v">' + DUNGEON_DATA.length + '</span><span class="dng-hstat-l">Celkem</span></div><div class="dng-hstat-sep"></div><div class="dng-hstat"><span class="dng-hstat-v c-red">' + (DUNGEON_DATA.length - unlockedCount) + '</span><span class="dng-hstat-l">Čeká</span></div></div></div></div><div class="dng-roadmap">' + DUNGEON_DATA.map((d, i) => renderDungeonNode(d, unlocked.has(d.attunement_id), i)).join('') + '</div>';
  } catch(e) {
    console.error('[Dungeons] Render error:', e);
    el.innerHTML = '<div style="color:var(--accent2);text-align:center;padding:30px;font-size:.85rem">⚠ Chyba</div>';
  }
}

function renderDungeonNode(d, isUnlocked, idx) {
  const connector = idx < DUNGEON_DATA.length - 1 ? '<div class="dng-connector"><div class="dng-connector-line" style="background:linear-gradient(to bottom,' + d.color + '66,' + DUNGEON_DATA[idx+1].color + '66)"></div><div class="dng-connector-nodes"><span class="dng-cn-dot" style="background:' + d.color + '"></span><span class="dng-cn-chain">⛓</span><span class="dng-cn-dot" style="background:' + DUNGEON_DATA[idx+1].color + '"></span></div></div>' : '';

  if (isUnlocked) {
    return '<div class="dng-node dng-unlocked" style="--dc:' + d.color + ';background:' + d.bg + '"><div class="dng-node-shimmer"></div><div class="dng-top-bar" style="background:linear-gradient(90deg,' + d.color + '44,' + d.color + '11,transparent)"><span class="dng-torch">' + d.torches[0] + '</span><span class="dng-status-badge unlocked">🔓 Odemčeno</span><span class="dng-torch">' + d.torches[1] + '</span></div><div class="dng-header"><div class="dng-portal" style="--dc:' + d.color + '"><div class="dng-portal-ring"></div><div class="dng-portal-icon">' + d.icon + '</div></div><div class="dng-header-text"><div class="dng-subtitle" style="color:' + d.color + '">' + esc(d.subtitle) + '</div><div class="dng-name">' + esc(d.name) + '</div><div class="dng-atm-row">' + d.atm.map(a => '<span class="dng-atm-chip" style="border-color:' + d.color + '44;color:' + d.color + '">' + a[0] + ' ' + esc(a[1]) + '</span>').join('') + '</div></div><div class="dbadge ' + d.diff_class + ' dng-diff">' + esc(d.difficulty) + '</div></div><div class="dng-body"><p class="dng-desc">' + esc(d.desc) + '</p><div class="dng-flavor" style="border-left-color:' + d.color + '66">' + esc(d.flavor) + '</div><div class="dng-info-grid"><div class="dng-info-card"><span class="dng-info-icon">⚔️</span><span class="dng-info-val">Lv. ' + d.min_level + '+</span><span class="dng-info-lbl">Min. level</span></div><div class="dng-info-card"><span class="dng-info-icon">🏰</span><span class="dng-info-val">' + d.floors + '</span><span class="dng-info-lbl">Pater</span></div><div class="dng-info-card"><span class="dng-info-icon">' + d.boss_icon + '</span><span class="dng-info-val" style="font-size:.65rem">' + esc(d.boss_name) + '</span><span class="dng-info-lbl">Boss</span></div></div><div class="dng-rewards-wrap"><div class="dng-rewards-title">🎁 Odměny</div><div class="dng-rewards-list">' + d.rewards.map(r => '<span class="dng-reward-chip" style="border-color:' + d.color + '55;color:' + d.color + '">' + esc(r) + '</span>').join('') + '</div></div></div><div class="dng-footer"><div class="dng-att-pill" style="border-color:' + d.color + '44;background:' + d.color + '0e"><span>' + d.attunement_badge + '</span><span>' + esc(d.attunement_name) + ' — Splněno ✓</span></div><button class="dng-enter-btn" style="--dc:' + d.color + '" onclick="enterDungeonRun(\'' + d.dungeon_key + '\', this)">⚔️ Vstoupit</button></div></div>' + connector;
  } else {
    return '<div class="dng-node dng-locked"><div class="dng-fog"></div><div class="dng-top-bar" style="background:rgba(255,255,255,.02)"><span class="dng-torch" style="opacity:.25">🕯️</span><span class="dng-status-badge locked">🔒 Zamčeno</span><span class="dng-torch" style="opacity:.25">🕯️</span></div><div class="dng-header"><div class="dng-portal locked"><div class="dng-portal-icon" style="filter:grayscale(1) brightness(.35)">🔒</div></div><div class="dng-header-text"><div class="dng-subtitle locked">???</div><div class="dng-name locked">' + esc(d.name) + '</div><div class="dng-atm-row">' + d.atm.map(a => '<span class="dng-atm-chip locked">' + a[0] + ' ' + esc(a[1]) + '</span>').join('') + '</div></div><div class="dbadge ' + d.diff_class + ' dng-diff" style="opacity:.4">' + esc(d.difficulty) + '</div></div><div class="dng-body"><p class="dng-desc locked">' + esc(d.desc) + '</p><div class="dng-info-grid"><div class="dng-info-card locked"><span class="dng-info-icon">⚔️</span><span class="dng-info-val">Lv. ' + d.min_level + '+</span><span class="dng-info-lbl">Min. level</span></div><div class="dng-info-card locked"><span class="dng-info-icon">🏰</span><span class="dng-info-val">' + d.floors + '</span><span class="dng-info-lbl">Pater</span></div><div class="dng-info-card locked"><span class="dng-info-icon">⚔️</span><span class="dng-info-val" style="font-size:.65rem">???</span><span class="dng-info-lbl">Boss</span></div></div><div class="dng-requirement"><div class="dng-req-icon">⛓️</div><div><div class="dng-req-title">Vyžaduje Attunement</div><div class="dng-req-chain">' + d.attunement_badge + ' ' + esc(d.attunement_name) + '</div><div class="dng-req-hint">Splň sérii questů v sekci <strong>Attunement</strong> pro odemknutí</div></div></div></div><div class="dng-footer"><div></div><button class="dng-att-btn" onclick="showPage(\'attunement\')">🔑 Jít na Attunement</button></div></div>' + connector;
  }
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
