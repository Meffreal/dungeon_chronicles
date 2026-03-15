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
