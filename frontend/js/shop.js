// ── NPC OBCHOD ────────────────────────────────────────────────────────────

// ── Shop NPC visual config ──
const SHOP_NPC_STYLES = {
  blacksmith: { artClass:'snpc-art--smith', color:'#e07030', rgb:'224,112,48',
    speech:'Nejlepší zbraně v kraji. Bez diskuze.' },
  alchemist:  { artClass:'snpc-art--alch',  color:'#40d870', rgb:'64,216,112',
    speech:'Moje lektvary prodlouží tvůj život... nebo zkrátí nepřítelův.' },
  trader:     { artClass:'snpc-art--trader', color:'#a060f0', rgb:'160,96,240',
    speech:'Vzácné věci z daleké země. Jen pro vás, příteli.' },
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
  let s = seconds;
  const tick = () => {
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
      if (timerEl) timerEl.classList.remove('shop-timer-urgent');
      loadShop();
      return;
    }
    s--;
  };
  tick();
  shopRotTimer = setInterval(tick, 1000);
}

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
          <div class="snpc-avatar">${npc.emoji}</div>
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
