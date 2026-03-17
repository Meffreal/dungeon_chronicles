// ── GLOBÁLNÍ STAV ─────────────────────────────────────────────────────────
let char = null, questTimer = null, selCls = null, clsData = {};
let _prevGold = null, _prevXp = null, _prevLevel = null;


let invData = [], invFilter = 'all', invSort = 'rarity', sellInvId = null;
let mktCurrentPage = 1, mktTotalPages = 1;
let searchTimeout = null;

const CLS_N = { warrior:'Válečník', mage:'Mág', ranger:'Lovec' };
const CLS_E = { warrior:'⚔️', mage:'🔮', ranger:'🏹' };
const CLS_D = { warrior:'Silný bojovník. Vysoký HP a obrana.', mage:'Mistr magie. Devastující kouzla.', ranger:'Rychlý lovec. Kritické zásahy.' };
const RARITY_COL = { common:'#9d9d9d', uncommon:'#1eff00', rare:'#0070dd', epic:'#a335ee', legendary:'#ff8000', set:'#00d4ff' };
const RARITY_CZ  = { common:'Běžný', uncommon:'Neobvyklý', rare:'Vzácný', epic:'Epický', legendary:'Legendární', set:'Setový' };
const SLOT_ICONS = { weapon:'⚔️', helmet:'⛑️', armor:'🥋', gloves:'🧤', boots:'👢', ring:'💍', amulet:'🧿' };
const SLOT_CZ    = { weapon:'Zbraň', helmet:'Přilba', armor:'Brnění', gloves:'Rukavice', boots:'Boty', ring:'Prsten', amulet:'Amulet' };

// ── TOAST ─────────────────────────────────────────────────────────────────
function toast(msg, type='i', dur=3500) {
  const ic = {s:'✅',e:'❌',i:'ℹ️'};
  const el = document.createElement('div');
  el.className = `toast t${type}`;
  el.innerHTML = `<span>${ic[type]}</span><span>${msg}</span>`;
  document.getElementById('toasts').append(el);
  setTimeout(() => el.remove(), dur);
}

// ── MODAL ─────────────────────────────────────────────────────────────────
const openModal = (id) => {
  document.getElementById(id).classList.add('open');
  if (id === 'modal-create') {
    renderClsGrid();
    if (typeof renderFactionGrid === 'function') renderFactionGrid();
  }
};
const closeModal = id => document.getElementById(id).classList.remove('open');
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.overlay').forEach(m => m.addEventListener('click', e => {
    if (e.target === m && m.id !== 'modal-create') closeModal(m.id);
  }));
  initNavGroups();
  _initMobileUI();
});

// ── MOBILNÍ UI ────────────────────────────────────────────────────────────
const _MOB_GROUP_META = {
  combat:      { icon: '⚔️', label: 'Boj' },
  progression: { icon: '🎯', label: 'Postava' },
  social:      { icon: '👥', label: 'Sociální' },
  seasonal:    { icon: '🌟', label: 'Sezónní' },
  cosmetics:   { icon: '🎨', label: 'Kosmetika' },
};

function _isMobile() { return window.innerWidth <= 768; }

function _initMobileUI() {
  if (document.getElementById('mob-tabbar')) return;

  // ── Bottom tab bar ────────────────────────────────────────────────────
  const tabbar = document.createElement('div');
  tabbar.className = 'mob-tabbar';
  tabbar.id = 'mob-tabbar';
  tabbar.innerHTML = Object.entries(_MOB_GROUP_META).map(([id, m]) =>
    `<button class="mob-tab" id="mob-tab-${id}" onclick="openMobileDrawer('${id}')">
       <span class="mob-tab-icon">${m.icon}</span>
       <span class="mob-tab-label">${m.label}</span>
     </button>`
  ).join('');

  // ── Backdrop ──────────────────────────────────────────────────────────
  const backdrop = document.createElement('div');
  backdrop.className = 'mob-backdrop';
  backdrop.id = 'mob-backdrop';
  backdrop.onclick = closeMobileDrawer;

  // ── Nav drawer ────────────────────────────────────────────────────────
  const drawer = document.createElement('div');
  drawer.className = 'mob-drawer';
  drawer.id = 'mob-drawer';
  drawer.innerHTML = `
    <div class="mob-drawer-header">
      <span class="mob-drawer-title" id="mob-drawer-title"></span>
      <button class="mob-drawer-close" onclick="closeMobileDrawer()">✕</button>
    </div>
    <div class="mob-drawer-nav" id="mob-drawer-nav"></div>`;

  document.body.append(backdrop, drawer, tabbar);
}

function openMobileDrawer(groupId) {
  if (!_isMobile()) return;
  const meta = _MOB_GROUP_META[groupId];
  if (!meta) return;

  const drawer   = document.getElementById('mob-drawer');
  const backdrop = document.getElementById('mob-backdrop');
  const titleEl  = document.getElementById('mob-drawer-title');
  const navEl    = document.getElementById('mob-drawer-nav');
  if (!drawer) return;

  // Naplníme drawer nav položkami skupiny
  titleEl.textContent = `${meta.icon} ${meta.label}`;
  navEl.innerHTML = '';
  const src = document.getElementById(`ngbody-${groupId}`);
  if (src) {
    src.querySelectorAll('.nav-btn').forEach(btn => {
      const clone = btn.cloneNode(true);
      const orig = clone.getAttribute('onclick') || '';
      if (orig) clone.setAttribute('onclick', orig + '; closeMobileDrawer()');
      navEl.appendChild(clone);
    });
  }

  // Zvýrazníme aktivní tab
  document.querySelectorAll('.mob-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`mob-tab-${groupId}`)?.classList.add('active');

  drawer.classList.add('open');
  backdrop.classList.add('open');
}

function closeMobileDrawer() {
  document.getElementById('mob-drawer')?.classList.remove('open');
  document.getElementById('mob-backdrop')?.classList.remove('open');
  document.querySelectorAll('.mob-tab').forEach(t => t.classList.remove('active'));
}

// ── GROUPED NAVIGATION ────────────────────────────────────────────────────
const _NAV_GROUP_PAGES = {
  quests:'combat', arena:'combat', boss:'combat', dungeons:'combat', build:'combat',
  equipment:'progression', inventory:'progression', subclass:'progression',
  prestige:'progression', professions:'progression', attunement:'progression',
  guild:'social', faction:'social', market:'social', shop:'social',
  weekly:'seasonal', season:'seasonal', 'world-events':'seasonal', achievements:'seasonal',
  crystals:'cosmetics',
};
const _NAV_GROUPS = ['combat','progression','social','seasonal','cosmetics'];

function _getNavGroupState() {
  try { return JSON.parse(localStorage.getItem('dc_nav_groups') || '{}'); }
  catch { return {}; }
}
function _saveNavGroupState(state) {
  localStorage.setItem('dc_nav_groups', JSON.stringify(state));
}

function toggleNavGroup(id) {
  const body   = document.getElementById(`ngbody-${id}`);
  const header = document.getElementById(`ngh-${id}`);
  if (!body || !header) return;
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  header.classList.toggle('open', !isOpen);
  const state = _getNavGroupState();
  state[id] = !isOpen;
  _saveNavGroupState(state);
}

function initNavGroups() {
  const state = _getNavGroupState();
  _NAV_GROUPS.forEach(id => {
    const isOpen = id in state ? state[id] : (id === 'combat');
    const body   = document.getElementById(`ngbody-${id}`);
    const header = document.getElementById(`ngh-${id}`);
    if (body)   body.classList.toggle('open', isOpen);
    if (header) header.classList.toggle('open', isOpen);
  });
}

function _expandGroupForPage(name) {
  const groupId = _NAV_GROUP_PAGES[name];
  if (!groupId) return;
  const body   = document.getElementById(`ngbody-${groupId}`);
  const header = document.getElementById(`ngh-${groupId}`);
  if (body && !body.classList.contains('open')) {
    body.classList.add('open');
    header?.classList.add('open');
    const state = _getNavGroupState();
    state[groupId] = true;
    _saveNavGroupState(state);
  }
}

// ── FEATURE DISCOVERY TOOLTIPS ────────────────────────────────────────────
// Jednorázové informační tipy při prvním otevření každé stránky.
// Uloženo v localStorage jako dc_seen_tips = { "arena": true, ... }

const PAGE_TIPS = {
  quests:          'Questy jsou hlavní zdroj XP, zlata a vybavení. Vyber quest, počkej na dokončení, pak seber odměnu.',
  equipment:       'Přiděluj stat body tlačítky +. Nasazené předměty v slotů zvyšují bojové statistiky.',
  inventory:       'Inventář obsahuje všechny tvé předměty. Klikni na předmět pro equipnutí, prodej nebo použití.',
  market:          'Tržiště je hráčská burza. Prodávej přebytečné předměty a nakupuj od ostatních hráčů.',
  shop:            'Obchod nabízí items od NPC. Každý NPC má jiný sortiment — podívej se na všechny záložky.',
  arena:           'Aréna je asynchronní PvP. Útočíš na vybraného soupeře — jejich postava se brání automaticky dle statistik.',
  guild:           'Cech je sociální hub: guild chat, sdílené cíle (weekly quests) a bonusy pro všechny členy.',
  dungeons:        'Dungeony jsou 5-stagová dobrodružství s přenosem HP. Přežij všechny stagy bez obnovy životů.',
  boss:            'World Boss je kooperativní výzva — přispívej k oslabení bosse spolu s ostatními hráči pro velké odměny.',
  achievements:    'Achievementy sledují tvé pokroky a odemykají tituly, bonusy a crystaly. Zkontroluj skryté úkoly.',
  faction:         'Frakce ovlivňuje tvůj herní styl a odemyká exkluzivní questy. Reputace roste splněním frakčních questů.',
  attunement:      'Attunement chains jsou série questů, které odemknou přístup do uzamčených dungeonů.',
  professions:     'Profese jsou pasivní specializace s unikátními schopnostmi — každý quest nebo arena boj může spustit efekt.',
  weekly:          'Týdenní questy se resetují každý týden a nabízejí výrazně lepší odměny než denní questy.',
  season:          'Sezónní pass sleduje tvou aktivitu a odměňuje tě kosmetickými předměty za každý level aktivity.',
  'world-events':  'World Events jsou komunitní výzvy — splňuj cíle spolu se všemi hráči pro sdílené odměny a body příspěvku.',
  crystals:        'Crystaly jsou prémiová měna NEZÍSKANÁ koupí — vyděláváš je achievementy, sezónou a eventy. Bez P2W!',
  prestige:        'Prestiž je dostupná po dosažení max levelu. Reset postavy za trvalé bonusy a exkluzivní tituly.',
  subclass:        'Subclass je trvalá specializace třídy dostupná od levelu 10. Volba je nevratná — vyber pečlivě!',
  build:           'Combat Build zobrazuje kompletní bojový profil — strategii, talenty, effective stats a dungeon modifikátor.',
  support:         'Tato stránka transparentně ukazuje jak funguje monetizace, drop rates a herní mechaniky. Žádné skryté algoritmy.',
};

/**
 * Zobrazí jednorázový informační tip při prvním otevření stránky.
 * Vloží se na začátek stránky a zmizí po 7s nebo po kliknutí ✕.
 *
 * @param {string} pageId — ID stránky (bez předpony "page-")
 * @param {string} text   — text tipu (max 2 věty)
 */
function showFeatureTip(pageId, text) {
  if (!text) return;

  // Přečti/aktualizuj localStorage
  let seen = {};
  try { seen = JSON.parse(localStorage.getItem('dc_seen_tips') || '{}'); } catch {}
  if (seen[pageId]) return;
  seen[pageId] = true;
  try { localStorage.setItem('dc_seen_tips', JSON.stringify(seen)); } catch {}

  // Odstraň předchozí tip pokud existuje
  document.getElementById('feature-tip')?.remove();

  const el = document.createElement('div');
  el.id        = 'feature-tip';
  el.className = 'feature-tip';
  el.innerHTML = `
    <span class="ft-icon">💡</span>
    <span class="ft-text">${esc(text)}</span>
    <button class="ft-close" onclick="document.getElementById('feature-tip')?.remove()" title="Zavřít">✕</button>`;

  // Vlož na začátek aktivní stránky
  const page = document.getElementById(`page-${pageId}`);
  if (page) page.insertAdjacentElement('afterbegin', el);

  // Auto-zmizí po 7s
  setTimeout(() => el?.remove(), 7000);
}

// ── NAVIGACE ──────────────────────────────────────────────────────────────
function showPage(name) {
  console.log('[UI] showPage() called with:', name);
  closeMobileDrawer();
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active', 'page-entering'));
  document.querySelectorAll('.nav-btn[id]').forEach(b => b.classList.remove('active'));
  const target = document.getElementById(`page-${name}`);
  if (target) {
    target.classList.add('active', 'page-entering');
    setTimeout(() => target.classList.remove('page-entering'), 250);
  }
  document.getElementById(`nav-${name}`)?.classList.add('active');
  _expandGroupForPage(name);
  if (name === 'quests')        loadQuests();
  if (name === 'equipment')     { renderEquip(); loadInventory(); }  // renderEquip je async, fire-and-forget OK
  if (name === 'inventory')     loadInventory();
  if (name === 'market')        { loadMarket(); loadMyListings(); }
  if (name === 'shop')          loadShop();
  if (name === 'arena')         loadArena();
  if (name === 'guild')         loadGuild();
  if (name === 'achievements')  loadAchievements();
  if (name === 'notifications') loadNotifications();
  if (name === 'faction')       loadFaction();
  if (name === 'dungeons') {
    console.log('[UI] Calling loadDungeons() for dungeons page');
    loadDungeons();
  }
  if (name === 'attunement')    loadAttunement();
  if (name === 'professions')   loadProfessions();
  if (name === 'build')         loadBuild();
  if (name === 'overview')      loadHub();
  if (name === 'legacy-item') {
    document.getElementById('page-death')?.classList.remove('active');
    loadLegacyItems();
  }

  // Zobraz jednorázový discovery tip při prvním otevření stránky
  if (name !== 'overview') showFeatureTip(name, PAGE_TIPS[name]);
}

// ── UTILITY ───────────────────────────────────────────────────────────────
function set(id, v) { const e = document.getElementById(id); if(e) e.textContent = v; }
function setHTML(id, html) { const e = document.getElementById(id); if(e) e.innerHTML = html; }
function pct(id, p) { const e = document.getElementById(id); if(e) e.style.width = `${Math.max(0,Math.min(100,p))}%`; }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// ── LOADING STATES ────────────────────────────────────────────────────────
function showLoading(containerId, text = 'Načítám...') {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = `<div class="loading-state"><span class="loading-spinner"></span><span>${text}</span></div>`;
}
function hideLoading(containerId) {
  // Render funkce přepisuje innerHTML — voláme pro sémantiku nebo při chybě.
  const el = document.getElementById(containerId);
  if (el && el.querySelector('.loading-spinner')) el.innerHTML = '';
}

// ── PLAYER SEARCH AUTOCOMPLETE ────────────────────────────────────────────
// Generuje HTML pro políčko s autocomplete hledáním hráče.
// Skrytý input se stejným `id` uchovává vybrané char ID (číselná hodnota).
// Čtení: parseInt(document.getElementById(id).value)
function playerSearchHtml(id, placeholder = 'Jméno hráče...') {
  return `
    <div class="ps-wrap">
      <input type="text" class="pr-input ps-input" id="ps-text-${id}"
        placeholder="${placeholder}" autocomplete="off"
        oninput="psInput('${id}', this.value)"
        onblur="setTimeout(psClear, 150, '${id}')">
      <div class="ps-dropdown" id="ps-drop-${id}" style="display:none"></div>
      <input type="hidden" id="${id}">
    </div>`;
}

let _psTimer = null;

function psInput(id, q) {
  clearTimeout(_psTimer);
  document.getElementById(id).value = '';  // zrušit výběr při editaci
  if (q.length < 2) { psClear(id); return; }
  _psTimer = setTimeout(() => psSearch(id, q), 280);
}

async function psSearch(id, q) {
  try {
    const results = await api('GET', `/character/search?q=${encodeURIComponent(q)}`);
    const drop = document.getElementById(`ps-drop-${id}`);
    if (!drop) return;
    if (!results.length) {
      drop.innerHTML = '<div class="ps-no-result">Nic nenalezeno</div>';
      drop.style.display = 'block';
      return;
    }
    drop.innerHTML = results.map(c => `
      <div class="ps-item" onmousedown="psSelect('${id}', ${c.id}, ${JSON.stringify(c.name).replace(/"/g, '&quot;')})">
        <span class="ps-cls">${c.cls_emoji}</span>
        <span class="ps-name">${esc(c.name)}</span>
        <span class="ps-level">Lv.${c.level}</span>
      </div>`).join('');
    drop.style.display = 'block';
  } catch(e) { psClear(id); }
}

function psSelect(id, charId, name) {
  document.getElementById(`ps-text-${id}`).value = name;
  document.getElementById(id).value = charId;
  psClear(id);
}

function psClear(id) {
  const drop = document.getElementById(`ps-drop-${id}`);
  if (drop) drop.style.display = 'none';
}

// ── REWARD ANIMATIONS ─────────────────────────────────────────────────────
function _tweenGold(el, from, to) {
  if (!el) return;
  const dur  = 400;
  const t0   = performance.now();
  const diff = to - from;
  function step(now) {
    const t    = Math.min(1, (now - t0) / dur);
    const ease = 1 - (1 - t) * (1 - t) * (1 - t); // easeOutCubic
    el.textContent = Math.round(from + diff * ease).toLocaleString('cs');
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function _spawnRewardLabel(amount, type) {
  const anchorId = type === 'gold' ? 'tb-gold' : 'xp-strip';
  const anchor   = document.getElementById(anchorId);
  if (!anchor) return;
  const rect = anchor.getBoundingClientRect();
  const el   = document.createElement('div');
  el.className   = `reward-float-label reward-float-${type}`;
  el.textContent = type === 'gold'
    ? `+${amount.toLocaleString('cs')} G`
    : `+${amount.toLocaleString('cs')} XP`;
  el.style.left = `${rect.left + rect.width / 2}px`;
  el.style.top  = `${rect.top - 4}px`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1100);
}

// Offsesy pro 5 částic (gold = ventilátor dolů, xp = ventilátor nahoru/do stran)
const _PARTICLE_OFFSETS = {
  gold: [[-32, 28], [-14, 42], [0, 46], [14, 42], [32, 28]],
  xp:   [[-36, -8], [-18, -26], [0, -32], [18, -26], [36, -8]],
};

function _spawnRewardParticles(type) {
  const anchorId = type === 'gold' ? 'tb-gold' : 'xp-strip';
  const anchor   = document.getElementById(anchorId);
  if (!anchor) return;
  const rect    = anchor.getBoundingClientRect();
  const cx      = rect.left + rect.width / 2;
  const cy      = rect.top  + rect.height / 2;
  const symbols = type === 'gold' ? ['🪙', '💰', '✨'] : ['⭐', '✨', '💫'];
  const offsets = _PARTICLE_OFFSETS[type];
  offsets.forEach(([dx, dy], i) => {
    const p = document.createElement('span');
    p.className = 'reward-particle';
    p.textContent = symbols[i % symbols.length];
    p.style.setProperty('--dx', `${dx + (Math.random() * 8 - 4)}px`);
    p.style.setProperty('--dy', `${dy}px`);
    p.style.left           = `${cx}px`;
    p.style.top            = `${cy}px`;
    p.style.animationDelay = `${i * 55}ms`;
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 950 + i * 55);
  });
}

function _playLevelUpAnim(newLevel) {
  const flash = document.createElement('div');
  flash.className = 'level-up-flash';
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 900);
  const runes = document.createElement('div');
  runes.className = 'level-up-runes';
  runes.textContent = '✦ ᚱ ✦';
  document.body.appendChild(runes);
  setTimeout(() => runes.remove(), 960);
  document.querySelectorAll('.portrait-outer, .equip-portrait-outer').forEach(el => {
    el.classList.remove('portrait-level-glow');
    void el.offsetWidth; // restart animation
    el.classList.add('portrait-level-glow');
    setTimeout(() => el.classList.remove('portrait-level-glow'), 2000);
  });
  setTimeout(() => toast(`⬆️ Level Up! Dosáhl jsi levelu ${newLevel}!`, 's', 4000), 300);
}

// ── UPDATE UI ─────────────────────────────────────────────────────────────
function updateUI(c) {
  console.log('[UI] updateUI() called with char:', c.id, c.name);
  char = c;
  // Detekuj změny pro reward animace
  const _ag = _prevGold, _ax = _prevXp, _al = _prevLevel;
  _prevGold = c.gold; _prevXp = c.xp; _prevLevel = c.level;
  const goldGained = (_ag !== null && c.gold  > _ag) ? c.gold - _ag : 0;
  const xpGained   = (_ax !== null && c.xp   > _ax && c.level === _al) ? c.xp - _ax : 0;
  const leveledUp  = (_al !== null && c.level > _al);
  const cl = c.cls;
  document.getElementById('tb-char').style.display = 'flex';
  const titleHtml = c.current_title ? `<span class="char-title">[${esc(c.current_title)}]</span> ` : '';
  const nameColor  = c.crystal_name_color || null;
  const nameHtml   = nameColor
    ? `<span style="color:${nameColor}">${esc(c.name)}</span>`
    : esc(c.name);
  set('tb-avatar', CLS_E[cl]);
  const avatarEl = document.getElementById('tb-avatar');
  if (avatarEl) {
    avatarEl.dataset.cls = cl;
    const activeFrameTb = c.season_portrait_frame || c.prestige_portrait_frame || c.crystal_portrait_frame || null;
    if (activeFrameTb) avatarEl.dataset.frame = activeFrameTb;
    else delete avatarEl.dataset.frame;
  }
  setHTML('tb-name', titleHtml + nameHtml);
  set('tb-lvl', `Lv.${c.level}`); set('tb-cls', CLS_N[cl]);
  if (goldGained > 0) {
    _tweenGold(document.getElementById('tb-gold'), _ag, c.gold);
    _spawnRewardLabel(goldGained, 'gold');
    _spawnRewardParticles('gold');
  } else {
    set('tb-gold', c.gold.toLocaleString('cs'));
  }
  if (c.crystals != null) {
    const crystalsEl = document.getElementById('tb-crystals');
    if (crystalsEl) crystalsEl.style.display = '';
    set('tb-crystals-val', c.crystals.toLocaleString('cs'));
  }

  // Use DiceBear avatar if appearance is available
  const avatarImg = document.getElementById('p-avatar-img');
  const avatarEmoji = document.getElementById('p-emoji');
  
  // Portrait frame — pořadí priority: season > prestige > crystal
  const ALL_FRAME_KEYS = [
    'bronze','silver','gold','arcane','ruby','legendary',
    'season-champion','season-challenger','season-veteran',
    'prestige-1','prestige-2','prestige-3','prestige-4','prestige-5',
    'prestige-6','prestige-7','prestige-8','prestige-9','prestige-10',
  ];
  const activeFrame = c.season_portrait_frame || c.prestige_portrait_frame || c.crystal_portrait_frame || null;
  document.querySelectorAll('.portrait-outer, .equip-portrait-outer').forEach(el => {
    ALL_FRAME_KEYS.forEach(k => el.classList.remove('pf-' + k));
    if (activeFrame) el.classList.add('pf-' + activeFrame);
  });

  if (avatarImg && c.appearance) {
    console.log('[UI] c.appearance:', c.appearance);
    console.log('[UI] c.appearance keys:', Object.keys(c.appearance));
    const url = getAvatarUrl(c.appearance, c.id);
    console.log('[UI] getAvatarUrl returned:', url);
    console.log('[UI] Setting avatar URL on #p-avatar-img');
    avatarImg.src = url;
    avatarImg.style.display = 'block';
    
    // Setup error handling
    avatarImg.onerror = function() {
      console.error('[UI] Avatar failed to load from:', this.src);
      this.style.display = 'none';
      if (avatarEmoji) avatarEmoji.style.display = 'block';
    };
    
    avatarImg.onload = function() {
      console.log('[UI] Avatar loaded successfully from:', this.src);
      if (avatarEmoji) avatarEmoji.style.display = 'none';
    };
  } else if (avatarEmoji) {
    console.log('[UI] Appearance not available or no avatar img, showing emoji fallback');
    // Fallback to emoji
    const avatarEmojiText = (typeof getAppearanceAvatar === 'function' && c.appearance)
      ? getAppearanceAvatar(c.appearance)
      : CLS_E[cl];
    if (avatarImg) avatarImg.style.display = 'none';
    avatarEmoji.style.display = 'block';
    set('p-emoji', avatarEmojiText);
  }
  
  setHTML('p-name', titleHtml + nameHtml);
  set('p-level', `Level ${c.level}`);
  // XP strip
  const xpPct = c.xp_to_next > 0 ? Math.min(100, (c.xp / c.xp_to_next) * 100) : 0;
  const stripFill = document.getElementById('xp-strip-fill');
  const stripLbl = document.getElementById('xp-strip-lbl');
  if (stripFill) stripFill.style.width = xpPct.toFixed(1) + '%';
  if (stripLbl) stripLbl.textContent = `Lv.${c.level} · ${c.xp} / ${c.xp_to_next} XP (${Math.floor(xpPct)}%)`;
  const strip = document.getElementById('xp-strip');
  if (strip) strip.title = `Lv.${c.level} · ${c.xp} / ${c.xp_to_next} XP`;

  set('ov-level', c.level);
  set('ov-xp', `${c.xp} / ${c.xp_to_next} XP`);
  set('ov-gold', c.gold.toLocaleString('cs') + ' G');
  set('ov-arena', `#${c.arena.rank}`); set('ov-wl', `${c.arena.wins}W / ${c.arena.losses}L`);
  set('ov-cls', `${CLS_E[cl]} ${CLS_N[cl]}`); set('ov-desc', CLS_D[cl]);
  set('ov-name', c.name);
  // Dashboard avatar (emoji fallback)
  const dashAvatar = document.getElementById('dash-avatar');
  if (dashAvatar) dashAvatar.textContent = CLS_E[cl] || '⚔';
  // Dashboard XP bar
  const xpFill = document.getElementById('dash-xp-fill');
  if (xpFill) xpFill.style.width = `${Math.max(2, Math.min(100, (c.xp / c.xp_to_next) * 100))}%`;
  // Pending actions
  _updateDashPending(c);

  // Frakce v přehledu
  const ovFaction = document.getElementById('ov-faction');
  if (ovFaction) {
    const fRep = factionData?.reputation ?? 0;
    ovFaction.innerHTML = typeof getFactionChipHtml === 'function'
      ? getFactionChipHtml(c.faction, fRep)
      : (c.faction || 'Bez frakce');
  }

  // Vzhled v přehledu
  if (c.appearance && document.getElementById('ov-appearance')) {
    const appearanceDisplay = _getAppearanceDisplayText(c.appearance);
    set('ov-appearance', appearanceDisplay);
  }

  renderActiveBuffs(c.active_buffs || []);

  // Stat points nav badge + propagace do group headeru
  const spBadge = document.getElementById('sp-nav-badge');
  const hasPoints = (c.stat_points || 0) > 0;
  if (spBadge) spBadge.classList.toggle('visible', hasPoints);
  const gBadge = document.getElementById('ngn-progression');
  if (gBadge) {
    gBadge.style.display = hasPoints ? 'flex' : 'none';
    gBadge.textContent = hasPoints ? c.stat_points : '';
  }

  // Arena rank chip — show when rank is notable (top 100 = rank ≤ 100 usually)
  const rankChip = document.getElementById('tb-rank-chip');
  const rankVal  = document.getElementById('tb-rank-val');
  if (rankChip && rankVal) {
    rankVal.textContent = `#${c.arena?.rank ?? '—'}`;
    rankChip.style.display = 'flex';
  }

  // Pokud je Vybavení otevřené, překresli ho (obsahuje atributy a stat body)
  if (document.getElementById('page-equipment')?.classList.contains('active')) {
    if (typeof renderEquip === 'function') renderEquip();
  }

  // XP a Level Up animace — na konci aby neblokoval hlavní render
  if (xpGained > 0) {
    _spawnRewardLabel(xpGained, 'xp');
    _spawnRewardParticles('xp');
  }
  if (leveledUp) {
    _playLevelUpAnim(c.level);
  }
}

// ── DASHBOARD PENDING ACTIONS ──────────────────────────────────────────────
function _updateDashPending(c) {
  const el = document.getElementById('dash-pending-actions');
  if (!el) return;
  const actions = [];

  if ((c.stat_points || 0) > 0) {
    actions.push({
      ico: '⬆', urgent: true,
      txt: `<strong>${c.stat_points} ${c.stat_points === 1 ? 'bod' : 'body'} k přidělení</strong> — zvyš si statistiky`,
      page: 'equipment',
    });
  }

  if (!c.equipment?.weapon && !c.equipment?.armor) {
    actions.push({ ico: '🛡', urgent: false, txt: 'Navštiv <strong>Obchod</strong> nebo <strong>Tržiště</strong> pro vybavení', page: 'shop' });
  }

  if ((c.arena?.cooldown_until) === null) {
    actions.push({ ico: '🏟', urgent: false, txt: 'Jsi připraven do <strong>Arény</strong> — máš dostupné souboje', page: 'arena' });
  }

  if (actions.length === 0) {
    el.innerHTML = '<div class="dash-pending-empty">✓ Vše v pořádku — žádné čekající akce</div>';
    return;
  }

  el.innerHTML = actions.map(a => `
    <div class="dash-pending-item ${a.urgent ? 'urgent' : ''}" onclick="showPage('${a.page}')">
      <span class="dash-pending-ico">${a.ico}</span>
      <span class="dash-pending-txt">${a.txt}</span>
      <span style="color:var(--text3);font-size:.7rem">→</span>
    </div>
  `).join('');
}

// ── SYNC ACTIVITY LOG TO DASHBOARD ────────────────────────────────────────
function _syncDashActivity() {
  const dst = document.getElementById('dash-recent-activity');
  if (!dst || !window._actLog?.length) return;
  dst.innerHTML = window._actLog.slice(0, 6).map(e =>
    `<div class="dash-activity-row">
      <span class="dash-activity-time">${e.t}</span>
      <span class="dash-activity-txt">${esc(e.text)}</span>
    </div>`
  ).join('');
}

function _getAppearanceDisplayText(appearance) {
  if (!appearance) return 'Standardní vzhled';
  
  // Pokud máme načtené možnosti, použij je
  if (window.appearanceOptions) {
    const opts = window.appearanceOptions;
    const parts = [];
    
    if (appearance.hair_style !== undefined && opts.hair_styles[appearance.hair_style]) {
      parts.push(`<strong>Vlasy:</strong> ${opts.hair_styles[appearance.hair_style].name}`);
    }
    if (appearance.skin_tone !== undefined && opts.skin_tones[appearance.skin_tone]) {
      parts.push(`<strong>Pokožka:</strong> ${opts.skin_tones[appearance.skin_tone].name}`);
    }
    if (appearance.eye_color !== undefined && opts.eye_colors[appearance.eye_color]) {
      parts.push(`<strong>Oči:</strong> ${opts.eye_colors[appearance.eye_color].name}`);
    }
    
    return parts.length ? parts.join(' · ') : 'Přizpůsobený vzhled';
  }
  
  // Fallback: struktura bez překladu
  return 'Vlastní vzhled';
}

// ── AKTIVNÍ BUFFY ─────────────────────────────────────────────────────────
function renderActiveBuffs(buffs) {
  const chip  = document.getElementById('tb-buff-chip');
  const count = document.getElementById('tb-buff-count');
  const drop  = document.getElementById('tb-buff-dropdown');
  if (!chip) return;
  if (!buffs || buffs.length === 0) { chip.style.display = 'none'; return; }

  const STAT_N = {bonus_str:'Síla',bonus_dex:'Obratnost',bonus_int:'Inteligence',bonus_end:'Výdrž',bonus_luck:'Štěstí'};
  chip.style.display = 'flex';
  count.textContent  = buffs.length;

  drop.innerHTML = buffs.map(b => {
    const exp  = new Date((b.expires_at.includes('T') && !b.expires_at.endsWith('Z')) ? b.expires_at + 'Z' : b.expires_at);
    const diff = exp - new Date();
    const days = Math.floor(diff / 86400000);
    const hrs  = Math.floor((diff % 86400000) / 3600000);
    const mins = Math.floor((diff % 3600000)  / 60000);
    const timeStr = diff <= 0 ? 'Expirováno'
                  : days > 0  ? `${days}d ${hrs}h`
                  : hrs  > 0  ? `${hrs}h ${mins}m`
                  : `${mins}m`;
    const bons = Object.entries(STAT_N)
      .filter(([k]) => b[k] > 0)
      .map(([k,n]) => `+${b[k]} ${n}`).join(' · ');
    return `<div class="tb-buff-entry">
      <span class="tb-buff-entry-name">⚗️ ${esc(b.name)}</span>
      <span class="tb-buff-entry-bonuses">${bons || '—'}</span>
      <span class="tb-buff-entry-timer${diff <= 0 ? ' expired' : ''}">⏰ ${timeStr}</span>
    </div>`;
  }).join('');
}

function toggleBuffDropdown(e) {
  e.stopPropagation();
  const drop = document.getElementById('tb-buff-dropdown');
  if (!drop) return;
  drop.classList.toggle('open');
}

// Zavři dropdown při kliknutí mimo
document.addEventListener('click', () => {
  const drop = document.getElementById('tb-buff-dropdown');
  if (drop) drop.classList.remove('open');
});
