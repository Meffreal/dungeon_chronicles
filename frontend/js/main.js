// ── INIT ──────────────────────────────────────────────────────────────────
document.addEventListener('contextmenu', e => e.preventDefault());

// ── GLOBAL ERROR HANDLERS ─────────────────────────────────────────────────
window.addEventListener('unhandledrejection', event => {
  const reason = event.reason;
  // API chyby mají err.status — jsou ošetřeny v try/catch blocích, ignoruj je
  if (reason && reason.status) return;
  console.error('[Unhandled rejection]', reason);
  if (typeof toast === 'function') {
    toast('Něco se pokazilo. Zkus to znovu.', 'e', 5000);
  }
});

window.addEventListener('error', event => {
  // Ignoruj chyby z externích zdrojů (avatary, CDN)
  if (event.filename && !event.filename.includes(window.location.host)) return;
  console.error('[JS Error]', event.message, event.filename, event.lineno);
});

async function heartbeat() {
  try {
    const r = await api('POST', '/auth/heartbeat');
    const el = document.getElementById('tb-online-count');
    if (el) el.textContent = r.online;
  } catch(e) {}
}

function startHeartbeat() {
  heartbeat();
  setInterval(heartbeat, 30_000);
}

async function init(){
  if(!token){location.href='/';return;}

  // 1. Třídy + frakce info — vždy první (pro modal tvorby postavy)
  loadCls();
  try {
    const info = await api('GET', '/faction/info');
    allFactions = info.factions;
  } catch(e) {}

  // 2. Zkus načíst postavu ze serveru
  let charLoaded = false;
  try{
    const c = await api('GET','/character/me');
    updateUI(c);
    charLoaded = true;
    addAct('👋 Přihlášen do dungeonu.');
    loadNotifications();
    startNotifPolling();
    startHeartbeat();
    loadHub();
    // Onboarding průvodce pro hráče kteří ho nedokončili
    if (!c.onboarding_completed && typeof startOnboarding === 'function') {
      setTimeout(() => startOnboarding(), 1200);
    }
    // Načti frakční data (pro overview chip a equipment badge)
    try {
      const fd = await api('GET', '/faction/my');
      factionData = fd;
      // Překresli ov-faction po načtení reputace
      const ovFaction = document.getElementById('ov-faction');
      if (ovFaction && typeof getFactionChipHtml === 'function') {
        ovFaction.innerHTML = getFactionChipHtml(c.faction, fd.reputation || 0);
      }
    } catch(e) {}
    // Načti guild info pro portrait
    try {
      const gd = await api('GET', '/guild/my');
      if (gd.guild) set('portrait-guild-name', `${gd.guild.emblem} ${gd.guild.name}`);
    } catch(e) {}
    try {
      const qs = await api('GET', '/quest/status');
      if (qs.status !== 'idle') {
        addAct(`⚔ Probíhá: ${qs.quest?.name || 'quest'}`);
        if (typeof renderAQ === 'function') renderAQ(qs);
      }
    } catch(e) {}
  } catch(e) {
    console.log('Postava nenalezena, otvírám modal:', e.message);
  }

  // 3. Pokud postava neexistuje — otevři modal
  if (!charLoaded) {
    localStorage.removeItem('dc_new_user');
    openModal('modal-create');
  }
}

init();

// ── B.5 — Death Screen ─────────────────────────────────────────────────────
function showDeathScreen(char) {
  const nameEl    = document.getElementById('death-hero-name');
  const infoEl    = document.getElementById('death-hero-info');
  const killedEl  = document.getElementById('death-killed-by');
  const screen    = document.getElementById('page-death');

  if (nameEl) nameEl.textContent = char.name || 'Hrdina';

  const days = char.days_survived !== undefined
    ? char.days_survived
    : (() => {
        const createdAt = char.created_at ? new Date(char.created_at) : new Date();
        const diedAt    = char.died_at    ? new Date(char.died_at)    : new Date();
        return Math.max(0, Math.floor((diedAt - createdAt) / (1000 * 60 * 60 * 24)));
      })();

  if (infoEl)   infoEl.textContent   = `Level ${char.level || 1} ${char.cls || 'Warrior'} · přežil ${days} dní`;
  if (killedEl) killedEl.textContent = `Zabit: ${char.killed_by || 'Neznámý nepřítel'}`;

  // Skryj vše ostatní, zobraz death screen jako stránku
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  if (screen) screen.classList.add('active');

  document.getElementById('death-new-run-btn')?.addEventListener('click', () => {
    if (screen) screen.classList.remove('active');
    openModal('modal-create');
  }, { once: true });
}

// ── B.6 — Legacy Item ──────────────────────────────────────────────────────

async function loadLegacyItems() {
  const el = document.getElementById('legacy-content');
  if (!el) return;
  el.innerHTML = '<div class="inv-empty">Načítám inventář...</div>';

  try {
    const pending = await api('GET', '/character/legacy/pending');
    if (pending.has_legacy) {
      renderLegacyPending(el, pending.item);
      return;
    }

    const inv = await api('GET', '/inventory/');
    const items = (inv.items || []);

    if (items.length === 0) {
      el.innerHTML = `
        <div class="legacy-empty-msg">
          <p>Tvůj hrdina neměl žádné předměty k odkázání.</p>
          <button class="btn btn--primary" onclick="startNewRun()">☩ Nový Run</button>
        </div>`;
      return;
    }

    renderLegacyGrid(el, items);
  } catch (err) {
    el.innerHTML = '<div class="inv-empty">Chyba při načítání inventáře.</div>';
    console.error('[Legacy] load error:', err);
  }
}

function renderLegacyGrid(el, items) {
  const UPGRADE_BADGE = ['', '★', '★★', '★★★'];

  const grid = items.map(inv => {
    const item = inv.item;
    const rc   = RARITY_COL[item?.rarity] || '#9d9d9d';
    const ul   = inv.upgrade_level || 0;
    const bonuses  = Object.entries(item?.bonuses || {}).filter(([, v]) => v > 0);
    const bonusTxt = bonuses.slice(0, 3).map(([k, v]) => `+${v} ${k.toUpperCase()}`).join(' · ');
    const chain    = inv.legacy_chain || [];

    return `<div class="inv-card legacy-selectable" style="--rc:${rc}"
              onclick="confirmSelectLegacy(${inv.id}, ${JSON.stringify(item?.name || '?')})">
      <div class="inv-card-icon">${item?.icon || '📦'}</div>
      <div class="inv-card-name" style="color:${rc}">${item?.name || '?'}</div>
      <div class="inv-card-type">${SLOT_CZ[item?.type] || item?.type || ''}</div>
      <div class="inv-card-bonus">${bonusTxt}</div>
      ${ul > 0 ? `<div class="inv-upgrade-badge">${UPGRADE_BADGE[Math.min(ul, 3)]}</div>` : ''}
      ${chain.length > 0 ? `<div class="legacy-chain-badge">⛓ ${chain.length}</div>` : ''}
      <div class="legacy-select-hint">Vybrat</div>
    </div>`;
  }).join('');

  el.innerHTML = `
    <p class="legacy-intro-text">Tento předmět poputuje s tvým příštím hrdinou jako odkaz padlého.</p>
    <div class="inv-grid">${grid}</div>
    <div class="legacy-skip-wrap">
      <button class="btn btn--ghost" onclick="backToDeathScreen()">Přeskočit — začít bez dědictví</button>
    </div>`;
}

function renderLegacyPending(el, item) {
  const rc    = RARITY_COL[item?.rarity] || '#9d9d9d';
  const chain = item.legacy_chain || [];

  const chainHtml = chain.map(h => `
    <div class="legacy-chain-entry">
      <span>${CLS_E[h.hero_cls] || '⚔️'} <strong>${h.hero_name || '?'}</strong></span>
      <span class="legacy-chain-detail">Lvl ${h.hero_level || '?'} · ${h.dungeon || 'Neznámo'}</span>
    </div>`).join('');

  el.innerHTML = `
    <div class="legacy-pending-wrap">
      <p class="legacy-intro-text">Tento předmět čeká na tvého příštího hrdinu.</p>
      <div class="legacy-pending-card" style="--rc:${rc}">
        <div class="legacy-pending-icon">${item.icon || '📦'}</div>
        <div class="legacy-pending-name" style="color:${rc}">${item.name || '?'}</div>
        <div class="legacy-pending-rarity">${RARITY_CZ[item.rarity] || ''} ${SLOT_CZ[item.type] || ''}</div>
        ${chain.length > 0 ? `
          <div class="legacy-chain-history">
            <div class="legacy-chain-title">Předchozí nositelé:</div>
            ${chainHtml}
          </div>` : ''}
      </div>
      <button class="btn btn--primary" onclick="startNewRun()">☩ Nový Run</button>
    </div>`;
}

async function confirmSelectLegacy(invItemId, itemName) {
  if (!confirm(`Vybrat "${itemName}" jako dědictví pro příštího hrdinu?`)) return;
  try {
    await api('POST', '/character/legacy/select', { item_id: invItemId });
    toast('Dědictví uloženo! Příští hrdina ponese odkaz.', 's');
    loadLegacyItems();
  } catch (err) {
    toast(err?.detail || 'Chyba při výběru dědictví.', 'e');
  }
}

function backToDeathScreen() {
  document.getElementById('page-legacy-item')?.classList.remove('active');
  document.getElementById('page-death')?.classList.add('active');
}

function startNewRun() {
  document.getElementById('page-legacy-item')?.classList.remove('active');
  document.getElementById('page-death')?.classList.remove('active');
  openModal('modal-create');
}
