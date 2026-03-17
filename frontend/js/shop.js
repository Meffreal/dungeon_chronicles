// ── NPC OBCHOD ────────────────────────────────────────────────────────────

// ── Shop NPC visual config ──
const SHOP_NPC_STYLES = {
  blacksmith: {
    artClass:'snpc-art--smith', color:'#e07030', rgb:'224,112,48',
    speech:'Nejlepší zbraně v kraji. Bez diskuze.',
    avatar:`<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="shp-smith-bg" cx="50%" cy="55%" r="55%"><stop offset="0%" stop-color="#e05010" stop-opacity=".4"/><stop offset="100%" stop-color="#3a0c00" stop-opacity="0"/></radialGradient>
        <radialGradient id="shp-smith-skin" cx="42%" cy="30%" r="60%"><stop offset="0%" stop-color="#b87848"/><stop offset="100%" stop-color="#7a4020"/></radialGradient>
        <radialGradient id="shp-smith-forge" cx="50%" cy="100%" r="60%"><stop offset="0%" stop-color="#ff6010" stop-opacity=".45"/><stop offset="100%" stop-color="#ff6010" stop-opacity="0"/></radialGradient>
        <linearGradient id="shp-smith-apron" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#5a3a1a"/><stop offset="100%" stop-color="#2a1808"/></linearGradient>
        <filter id="shp-smith-gf"><feGaussianBlur stdDeviation="2.5"/></filter>
      </defs>
      <ellipse cx="40" cy="52" rx="38" ry="48" fill="url(#shp-smith-bg)"/>
      <ellipse cx="40" cy="108" rx="42" ry="22" fill="url(#shp-smith-forge)"/>
      <path d="M4,100 Q6,58 40,50 Q74,58 76,100Z" fill="#1a0e06"/>
      <path d="M8,100 Q10,62 40,54 Q70,62 72,100Z" fill="#241408"/>
      <ellipse cx="13" cy="64" rx="16" ry="10" fill="#342010" transform="rotate(-10,13,64)"/>
      <ellipse cx="67" cy="64" rx="16" ry="10" fill="#342010" transform="rotate(10,67,64)"/>
      <path d="M32,54 L25,100" stroke="#6a4018" stroke-width="5.5" stroke-linecap="round"/>
      <path d="M48,54 L55,100" stroke="#6a4018" stroke-width="5.5" stroke-linecap="round"/>
      <path d="M25,73 Q40,68 55,73" stroke="#8a5820" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="M25,73 Q40,70 55,73" stroke="#a87030" stroke-width="1.2" fill="none"/>
      <rect x="33" y="48" width="14" height="10" rx="3" fill="#a06030"/>
      <ellipse cx="40" cy="35" rx="21" ry="24" fill="#b87050"/>
      <ellipse cx="40" cy="33" rx="19" ry="22" fill="url(#shp-smith-skin)"/>
      <path d="M19,28 Q22,7 40,5 Q58,7 61,28 Q52,14 40,12 Q28,14 19,28Z" fill="#1e1206"/>
      <path d="M19,26 Q22,9 40,7 Q58,9 61,26" fill="#2a1a0a"/>
      <path d="M17,34 Q15,22 20,14" stroke="#1e1206" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <path d="M63,34 Q65,22 60,14" stroke="#1e1206" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <path d="M23,25 Q30,21 37,24" stroke="#1e1206" stroke-width="3.2" fill="none" stroke-linecap="round"/>
      <path d="M43,24 Q50,21 57,25" stroke="#1e1206" stroke-width="3.2" fill="none" stroke-linecap="round"/>
      <ellipse cx="31" cy="30" rx="5.5" ry="3.8" fill="#e8d8b0"/>
      <ellipse cx="49" cy="30" rx="5.5" ry="3.8" fill="#e8d8b0"/>
      <ellipse cx="31" cy="30" rx="3.5" ry="2.5" fill="#804010"/>
      <ellipse cx="49" cy="30" rx="3.5" ry="2.5" fill="#804010"/>
      <ellipse cx="31" cy="30" rx="2" ry="1.6" fill="#1a0800"/>
      <ellipse cx="49" cy="30" rx="2" ry="1.6" fill="#1a0800"/>
      <circle cx="29.5" cy="28.5" r="1.3" fill="#fff" opacity=".85"/>
      <circle cx="47.5" cy="28.5" r="1.3" fill="#fff" opacity=".85"/>
      <path d="M37,34 Q40,38 43,34" stroke="#7a3818" stroke-width="1.1" fill="none"/>
      <line x1="26" y1="34" x2="29" y2="42" stroke="#a04828" stroke-width="2" stroke-linecap="round"/>
      <path d="M33,37 Q40,41 47,37" stroke="#904030" stroke-width="1.3" fill="none" stroke-linecap="round"/>
      <path d="M26,38 Q28,50 40,54 Q52,50 54,38 Q48,48 40,50 Q32,48 26,38Z" fill="#1e1206"/>
      <path d="M28,40 Q30,50 40,52 Q50,50 52,40 Q46,48 40,50 Q34,48 28,40Z" fill="#2a1a0a"/>
      <path d="M34,37 Q40,40 46,37" stroke="#1e1206" stroke-width="2.8" fill="none" stroke-linecap="round"/>
      <ellipse cx="22" cy="33" rx="3.5" ry="2" fill="#0a0604" opacity=".35" transform="rotate(-20,22,33)"/>
      <ellipse cx="57" cy="30" rx="2.5" ry="1.5" fill="#0a0604" opacity=".25" transform="rotate(15,57,30)"/>
      <ellipse cx="40" cy="95" rx="36" ry="16" fill="#ff5000" opacity=".07" filter="url(#shp-smith-gf)"/>
      <circle cx="7" cy="45" r="1.5" fill="#ff6010" opacity=".6"/>
      <circle cx="73" cy="52" r="1.2" fill="#e05010" opacity=".45"/>
      <circle cx="5" cy="74" r="1" fill="#ff4000" opacity=".4"/>
      <circle cx="74" cy="78" r="1" fill="#ff8020" opacity=".35"/>
    </svg>`,
  },
  alchemist: {
    artClass:'snpc-art--alch',  color:'#40d870', rgb:'64,216,112',
    speech:'Moje lektvary prodlouží tvůj život... nebo zkrátí nepřítelův.',
    avatar:`<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="shp-alch-bg" cx="50%" cy="40%" r="55%"><stop offset="0%" stop-color="#10c840" stop-opacity=".35"/><stop offset="100%" stop-color="#041808" stop-opacity="0"/></radialGradient>
        <radialGradient id="shp-alch-skin" cx="45%" cy="30%" r="60%"><stop offset="0%" stop-color="#a89870"/><stop offset="100%" stop-color="#706040"/></radialGradient>
        <filter id="shp-alch-gf"><feGaussianBlur stdDeviation="2"/></filter>
        <filter id="shp-alch-lgf"><feGaussianBlur stdDeviation="1.5"/></filter>
      </defs>
      <ellipse cx="40" cy="44" rx="36" ry="46" fill="url(#shp-alch-bg)"/>
      <path d="M8,100 Q12,58 40,50 Q68,58 72,100Z" fill="#0a1808"/>
      <path d="M12,100 Q16,62 40,54 Q64,62 68,100Z" fill="#0e2010"/>
      <path d="M14,78 Q40,72 66,78" stroke="#1a4018" stroke-width="1" fill="none" opacity=".55"/>
      <path d="M18,91 Q40,85 62,91" stroke="#1a4018" stroke-width=".8" fill="none" opacity=".4"/>
      <ellipse cx="67" cy="73" rx="5" ry="8" fill="#10c040" opacity=".65"/>
      <rect x="64.5" y="64" width="5" height="4" rx="1.5" fill="#204018"/>
      <circle cx="67" cy="69" r="2.2" fill="#80ff80" opacity=".5" filter="url(#shp-alch-lgf)"/>
      <path d="M18,55 Q20,42 40,38 Q60,42 62,55 Q52,49 40,51 Q28,49 18,55Z" fill="#0a2010"/>
      <rect x="35" y="47" width="10" height="10" rx="3" fill="#907860"/>
      <ellipse cx="40" cy="32" rx="17" ry="21" fill="#a09060"/>
      <ellipse cx="40" cy="30" rx="15" ry="19" fill="url(#shp-alch-skin)"/>
      <path d="M23,27 Q22,8 40,5 Q58,8 57,27 Q50,13 40,11 Q30,13 23,27Z" fill="#c8c8b0"/>
      <path d="M23,25 Q22,10 40,7 Q58,10 57,25" fill="#d8d8c0"/>
      <path d="M20,34 Q17,20 21,11" stroke="#d0d0c0" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <path d="M60,34 Q63,20 59,11" stroke="#d0d0c0" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <path d="M25,22 Q31,18 37,21" stroke="#c0c0b0" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M43,21 Q49,18 55,22" stroke="#c0c0b0" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="32" cy="27" r="6.2" fill="none" stroke="#6a5018" stroke-width="1.6"/>
      <circle cx="48" cy="27" r="6.2" fill="none" stroke="#6a5018" stroke-width="1.6"/>
      <line x1="38.2" y1="27" x2="41.8" y2="27" stroke="#6a5018" stroke-width="1.6"/>
      <line x1="25.8" y1="27" x2="22" y2="28.5" stroke="#6a5018" stroke-width="1.6"/>
      <line x1="54.2" y1="27" x2="58" y2="28.5" stroke="#6a5018" stroke-width="1.6"/>
      <circle cx="32" cy="27" r="5.5" fill="#20d060" opacity=".22" filter="url(#shp-alch-lgf)"/>
      <circle cx="48" cy="27" r="5.5" fill="#20d060" opacity=".22" filter="url(#shp-alch-lgf)"/>
      <ellipse cx="32" cy="27" rx="3.8" ry="2.7" fill="#cce8cc"/>
      <ellipse cx="48" cy="27" rx="3.8" ry="2.7" fill="#cce8cc"/>
      <ellipse cx="32" cy="27" rx="2.2" ry="1.9" fill="#108040"/>
      <ellipse cx="48" cy="27" rx="2.2" ry="1.9" fill="#108040"/>
      <ellipse cx="32" cy="27" rx="1.2" ry="1.1" fill="#041808"/>
      <ellipse cx="48" cy="27" rx="1.2" ry="1.1" fill="#041808"/>
      <circle cx="30.8" cy="25.8" r="1.1" fill="#fff" opacity=".85"/>
      <circle cx="46.8" cy="25.8" r="1.1" fill="#fff" opacity=".85"/>
      <path d="M39,33 Q37,37 39,39 Q40,40 41,39 Q43,37 41,33" stroke="#706040" stroke-width=".9" fill="none"/>
      <path d="M26,38 Q24,54 28,72 Q34,86 40,91 Q46,86 52,72 Q56,54 54,38 Q48,51 40,54 Q32,51 26,38Z" fill="#c8c8b8"/>
      <path d="M28,40 Q26,55 30,71 Q35,84 40,89 Q45,84 50,71 Q54,55 52,40 Q46,52 40,54 Q34,52 28,40Z" fill="#d8d8c8"/>
      <line x1="36" y1="56" x2="33" y2="82" stroke="#b8b8a8" stroke-width=".7" opacity=".5"/>
      <line x1="40" y1="57" x2="40" y2="86" stroke="#b8b8a8" stroke-width=".7" opacity=".5"/>
      <line x1="44" y1="56" x2="47" y2="82" stroke="#b8b8a8" stroke-width=".7" opacity=".5"/>
      <path d="M25,31 Q27,35 26,38" stroke="#706040" stroke-width=".9" fill="none" opacity=".5"/>
      <path d="M55,31 Q53,35 54,38" stroke="#706040" stroke-width=".9" fill="none" opacity=".5"/>
      <path d="M27,25 Q26,28 28,30" stroke="#706040" stroke-width=".7" fill="none" opacity=".4"/>
      <circle cx="7" cy="38" r="1.5" fill="#40ff80" opacity=".6"/>
      <circle cx="73" cy="34" r="1.2" fill="#20d060" opacity=".45"/>
      <circle cx="9" cy="68" r="1" fill="#10c040" opacity=".4"/>
      <circle cx="71" cy="60" r="1" fill="#30e070" opacity=".35"/>
    </svg>`,
  },
  trader: {
    artClass:'snpc-art--trader', color:'#a060f0', rgb:'160,96,240',
    speech:'Vzácné věci z daleké země. Jen pro vás, příteli.',
    avatar:`<svg viewBox="0 0 80 100" xmlns="http://www.w3.org/2000/svg" width="82" height="92" class="npc-portrait-svg">
      <defs>
        <radialGradient id="shp-trd-bg" cx="50%" cy="40%" r="55%"><stop offset="0%" stop-color="#8020e0" stop-opacity=".4"/><stop offset="100%" stop-color="#1a0440" stop-opacity="0"/></radialGradient>
        <radialGradient id="shp-trd-skin" cx="45%" cy="30%" r="60%"><stop offset="0%" stop-color="#9a7050"/><stop offset="100%" stop-color="#5a3820"/></radialGradient>
        <radialGradient id="shp-trd-hood" cx="50%" cy="0%" r="80%"><stop offset="0%" stop-color="#2a1050"/><stop offset="100%" stop-color="#0c0418"/></radialGradient>
        <filter id="shp-trd-gf"><feGaussianBlur stdDeviation="2.5"/></filter>
        <filter id="shp-trd-lgf"><feGaussianBlur stdDeviation="1.5"/></filter>
      </defs>
      <ellipse cx="40" cy="44" rx="36" ry="46" fill="url(#shp-trd-bg)"/>
      <path d="M4,100 Q8,58 40,50 Q72,58 76,100Z" fill="#100828"/>
      <path d="M8,100 Q12,62 40,54 Q68,62 72,100Z" fill="#180c38"/>
      <path d="M12,76 Q40,69 68,76" stroke="#4a2080" stroke-width="1.2" fill="none" opacity=".6"/>
      <path d="M16,89 Q40,82 64,89" stroke="#3a1870" stroke-width=".9" fill="none" opacity=".4"/>
      <circle cx="28" cy="69" r="2.2" fill="#c080ff" opacity=".6"/>
      <circle cx="52" cy="72" r="1.6" fill="#a060e0" opacity=".5"/>
      <circle cx="40" cy="79" r="1.2" fill="#d0a0ff" opacity=".4"/>
      <path d="M15,49 Q17,19 40,13 Q63,19 65,49 Q54,37 40,37 Q26,37 15,49Z" fill="url(#shp-trd-hood)"/>
      <path d="M17,51 Q19,23 40,17 Q61,23 63,51 Q52,39 40,39 Q28,39 17,51Z" fill="#1a0840"/>
      <path d="M17,51 Q18,29 33,21 Q27,31 25,51Z" fill="#0a0420" opacity=".72"/>
      <rect x="34" y="47" width="12" height="9" rx="3" fill="#7a5030"/>
      <ellipse cx="40" cy="33" rx="17" ry="20" fill="#9a7050"/>
      <ellipse cx="40" cy="31" rx="15" ry="18" fill="url(#shp-trd-skin)"/>
      <path d="M25,28 Q27,17 35,14 Q28,22 26,39Z" fill="#0a0420" opacity=".52"/>
      <path d="M27,23 Q33,19 39,22" stroke="#2a1808" stroke-width="2" fill="none" stroke-linecap="round" opacity=".35"/>
      <path d="M41,22 Q47,19 54,23" stroke="#2a1808" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <ellipse cx="31" cy="28" rx="4.5" ry="3.2" fill="#7a5840" opacity=".55"/>
      <ellipse cx="31" cy="28" rx="2.8" ry="2" fill="#3a2010" opacity=".55"/>
      <ellipse cx="49" cy="27" rx="5" ry="3.5" fill="#ecdcb0"/>
      <ellipse cx="49" cy="27" rx="3.2" ry="2.3" fill="#c07010"/>
      <ellipse cx="49" cy="27" rx="1.8" ry="1.5" fill="#1a0c00"/>
      <circle cx="47.6" cy="25.6" r="1.4" fill="#fff" opacity=".88"/>
      <path d="M38,33 Q36,37 38,39 Q40,40 42,39 Q44,37 42,33" stroke="#6a3818" stroke-width=".9" fill="none"/>
      <path d="M34,43 Q40,48 46,43" stroke="#7a4828" stroke-width="1.3" fill="none" stroke-linecap="round"/>
      <path d="M36,43 Q40,46 44,43" stroke="#a06040" stroke-width=".9" fill="none"/>
      <circle cx="57" cy="32" r="4" fill="#0a0420" opacity=".5" filter="url(#shp-trd-lgf)"/>
      <circle cx="57" cy="32" r="3" fill="#f0c030"/>
      <circle cx="55.8" cy="30.8" r="1.2" fill="#fff8c0" opacity=".75"/>
      <path d="M33,47 Q40,52 47,47" stroke="#d0a020" stroke-width="1.5" fill="none" opacity=".65"/>
      <circle cx="40" cy="51" r="2.2" fill="#c09018" opacity=".7"/>
      <text x="61" y="19" font-size="8" fill="#c080ff" opacity=".5" font-family="serif">✦</text>
      <text x="6" y="62" font-size="6" fill="#9050e0" opacity=".4" font-family="serif">✧</text>
      <text x="64" y="78" font-size="5" fill="#b070ff" opacity=".35" font-family="serif">✦</text>
      <circle cx="8" cy="38" r="1.5" fill="#c080ff" opacity=".6"/>
      <circle cx="72" cy="32" r="1.2" fill="#a060e0" opacity=".45"/>
      <circle cx="10" cy="68" r="1" fill="#8040c0" opacity=".4"/>
      <circle cx="71" cy="65" r="1" fill="#d0a0ff" opacity=".35"/>
    </svg>`,
  },
};
// Fallback pro neznámé NPC klíče
function _shopNpcStyle(npc) {
  const key = (npc.key || npc.name || '').toLowerCase();
  if (key.includes('smith') || key.includes('kovar') || key.includes('blacksmith'))
    return SHOP_NPC_STYLES.blacksmith;
  if (key.includes('alch')) return SHOP_NPC_STYLES.alchemist;
  return SHOP_NPC_STYLES.trader;
}

let shopRotTimer = null;
let _shopRotTarget = null;  // absolute ms timestamp when next rotation fires
let _shopData = null;
let _buyingItemId = null;  // request dedup: prevent double-buy

async function loadShop() {
  try {
    const d = await api('GET', '/shop/');
    _shopData = d;
    renderShop(d);
    startShopRotTimer(d.seconds_to_rotation);
  } catch(e) { toast(e.message, 'e'); }
}

function startShopRotTimer(seconds) {
  if (shopRotTimer) clearInterval(shopRotTimer);
  _shopRotTarget = Date.now() + seconds * 1000;
  const tick = () => {
    const s = Math.max(0, Math.round((_shopRotTarget - Date.now()) / 1000));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    const timeStr = h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`
                          : `${m}:${String(ss).padStart(2,'0')}`;
    set('shop-rot-time', timeStr);
    // Last 60s: pulse the timer to build urgency
    const timerEl = document.getElementById('shop-rot-time');
    if (timerEl) timerEl.classList.toggle('shop-timer-urgent', s <= 60);
    if (s <= 0) {
      clearInterval(shopRotTimer);
      shopRotTimer = null;
      _shopRotTarget = null;
      if (timerEl) timerEl.classList.remove('shop-timer-urgent');
      loadShop();
      return;
    }
  };
  tick();
  shopRotTimer = setInterval(tick, 1000);
}

// Po probuzení z hibernace / návratu z background tabu okamžitě refreshuje shop
// pokud je timer za cílovým časem (setInterval byl throttlován nebo zastaven)
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && _shopRotTarget !== null && Date.now() >= _shopRotTarget) {
    loadShop();
  }
});

let _activeShopNpcIdx = null;  // null = žádný expand

function selectShopNpc(idx) { toggleShopNpc(idx); }

function renderShop(data) {
  const wrap = document.getElementById('shop-npc-grid');
  if (!wrap) return;

  const cardsHtml = data.npcs.map((npc, i) => {
    const sty = _shopNpcStyle(npc);
    const isActive = _activeShopNpcIdx === i;
    return `
      <div class="snpc-card ${isActive ? 'snpc--active' : ''}"
           style="--snc-color:${sty.color};--snc-rgb:${sty.rgb}"
           onclick="toggleShopNpc(${i})">
        <div class="snpc-art ${sty.artClass}"></div>
        <div class="snpc-portrait-zone">
          <div class="snpc-avatar">${sty.avatar || npc.emoji}</div>
          <div class="snpc-name">${esc(npc.name)}</div>
          <div class="snpc-role">${esc(npc.role || 'Obchodník')}</div>
          <div class="snpc-speech">${sty.speech}</div>
        </div>
        <div class="snpc-overlay">
          <div class="snpc-stock">${npc.items.length} položek na skladě</div>
          <button class="snpc-open-btn" style="--snc-color:${sty.color};--snc-rgb:${sty.rgb}"
            onclick="event.stopPropagation();toggleShopNpc(${i})">
            ${isActive ? '✕ Zavřít obchod' : '🛒 Otevřít obchod'}
          </button>
        </div>
      </div>`;
  }).join('');

  const expandHtml = _activeShopNpcIdx !== null
    ? renderShopExpandPanel(data.npcs[_activeShopNpcIdx], _activeShopNpcIdx)
    : '';

  wrap.innerHTML = `
    <div class="shop-npc-board" id="snpc-board">${cardsHtml}</div>
    <div id="snpc-expand">${expandHtml}</div>`;

  // Skrýt původní rotation bar — rotace je teď v panelu
  const origBar = document.getElementById('shop-rotation-bar');
  if (origBar) origBar.style.display = 'none';
}

function toggleShopNpc(idx) {
  _activeShopNpcIdx = _activeShopNpcIdx === idx ? null : idx;
  if (_shopData) renderShop(_shopData);
}

function renderShopExpandPanel(npc, idx) {
  const sty = _shopNpcStyle(npc);
  return `
    <div class="snpc-expand-panel" style="--snc-color:${sty.color};--snc-rgb:${sty.rgb}">
      <div class="snpc-panel-header">
        <div class="snpc-panel-avatar">${npc.emoji}</div>
        <div class="snpc-panel-name">${esc(npc.name)}</div>
        <div class="snpc-rot-bar" style="flex:none;padding:4px 10px">
          <span class="snpc-rot-label">⏱ za</span>
          <span class="snpc-rot-time" id="shop-rot-time">—</span>
        </div>
        <button class="snpc-panel-close" onclick="toggleShopNpc(${idx})">✕</button>
      </div>
      <div class="snpc-panel-body">
        <div class="shop-item-grid">${renderShopItemCards(npc.items)}</div>
      </div>
    </div>`;
}

function renderShopItemCards(items) {
  if (!items || items.length === 0)
    return `<div class="empty-state-card">
  <div class="empty-state-icon">🕸</div>
  <div class="empty-state-title">Obchodník nemá zboží</div>
  <div class="empty-state-sub">Zásoby se obnoví při příští rotaci.</div>
</div>`;

  const RARITY_GLOW = {
    common:    '157,157,157',
    uncommon:  '30,255,0',
    rare:      '0,112,221',
    epic:      '163,53,238',
    legendary: '255,128,0',
  };
  const RARITY_LABEL = {
    common:'Obyčejný', uncommon:'Neobvyklý', rare:'Vzácný', epic:'Epický', legendary:'Legendární',
  };

  return items.map(item => {
    const rc  = item.rarity_color || '#9d9d9d';
    const rgb = RARITY_GLOW[item.rarity] || '157,157,157';
    const canAfford = char && char.gold >= item.shop_price;
    const bonuses = Object.entries(item.bonuses || {})
      .filter(([,v]) => v > 0)
      .map(([k,v]) => `<div class="shop-card-stat"><span class="shop-card-stat-key">${k.toUpperCase()}</span><span class="shop-card-stat-val">+${v}</span></div>`)
      .join('');

    return `
    <div class="shop-card ${canAfford ? '' : 'shop-card-broke'}" data-rarity="${item.rarity}"
         style="--rc:${rc};--rgb:${rgb}">
      <div class="shop-card-rarity-bar"></div>
      <div class="shop-card-icon">${item.icon}</div>
      <div class="shop-card-name" style="color:${rc}">${esc(item.name)}</div>
      <div class="shop-card-tags">
        <span class="shop-card-rarity">${RARITY_LABEL[item.rarity] || item.rarity}</span>
        <span class="shop-card-lvl">Lv.${item.min_level}+</span>
      </div>
      ${bonuses ? `<div class="shop-card-stats">${bonuses}</div>` : `<div class="shop-card-type">${item.type === 'potion' ? '🧪 Spotřební' : '📦 Vybavení'}</div>`}
      <div class="shop-card-footer">
        <div class="shop-card-price">
          <span class="shop-card-gold-ico">🪙</span>
          <span class="shop-card-gold-val" style="${canAfford ? '' : 'color:#e06060'}">${item.shop_price.toLocaleString('cs')} G</span>
        </div>
        <button class="shop-card-buy-btn ${canAfford ? '' : 'shop-card-buy-broke'}"
                ${canAfford ? '' : 'disabled'}
                onclick="buyFromShop(${item.id},'${esc(item.name)}',${item.shop_price},this)">
          ${canAfford ? 'Koupit' : 'Nemáš dost'}
        </button>
      </div>
    </div>`;
  }).join('');
}

async function buyFromShop(itemId, itemName, price, btnEl) {
  if (_buyingItemId === itemId) return;  // deduplicate rapid clicks
  _buyingItemId = itemId;
  if (btnEl) { btnEl.disabled = true; btnEl.textContent = '⏳'; }
  try {
    const d = await api('POST', '/shop/buy', { item_id: itemId });
    updateUI({ ...char, gold: d.gold_remaining });
    toast(`🛒 Zakoupeno: ${itemName} za ${price} G`, 's', 3500);
    addAct(`🏪 Koupeno od NPC: ${itemName} (−${price} G)`);
    // Animate card flash
    if (btnEl) {
      const card = btnEl.closest('.shop-card');
      if (card) { card.classList.add('shop-card-bought'); setTimeout(() => card.classList.remove('shop-card-bought'), 600); }
    }
    // Refresh shop state
    const fresh = await api('GET', '/shop/');
    _shopData = fresh;
    renderShop(fresh);
    startShopRotTimer(fresh.seconds_to_rotation);
  } catch(e) {
    toast(e.message, 'e');
    if (btnEl) { btnEl.disabled = false; btnEl.textContent = 'Koupit'; }
  } finally {
    _buyingItemId = null;
  }
}
