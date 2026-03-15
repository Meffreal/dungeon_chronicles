// ── CRYSTAL SHOP ──────────────────────────────────────────────────────────────
let _crystalData = null;

async function loadCrystals() {
  try {
    const d = await api('GET', '/crystals/shop');
    _crystalData = d;
    renderCrystalShop(d);
  } catch(e) { toast(e.message, 'e'); }
}

function renderCrystalShop(d) {
  const el = document.getElementById('page-crystals');
  if (!el) return;

  // Aktivní efekty
  let boostHtml = '';
  if (d.xp_boost_active && d.xp_boost_until) {
    const until = new Date(d.xp_boost_until + 'Z');
    const diffMs = until - Date.now();
    const h = Math.floor(diffMs / 3_600_000);
    const m = Math.floor((diffMs % 3_600_000) / 60_000);
    boostHtml = `
      <div class="crys-active-effect">
        ⚡ <strong>XP Posílení aktivní</strong>
        <span class="crys-boost-timer">ještě ${h}h ${m}m</span>
        <span class="crys-boost-pct">+25 % XP</span>
      </div>`;
  }

  let nameColorHtml = '';
  if (d.name_color) {
    nameColorHtml = `
      <div class="crys-active-effect">
        🎨 <strong>Barva jména:</strong>
        <span style="color:${d.name_color};font-weight:700">Aktivní</span>
        <button class="btn btn-sm crys-reset-btn" onclick="resetNameColor()">✕ Resetovat</button>
      </div>`;
  }

  let frameHtml = '';
  if (d.portrait_frame) {
    const FRAME_LABELS = {
      bronze: 'Bronzový rám', silver: 'Stříbrný rám', gold: 'Zlatý rám',
      arcane: 'Arkánný rám',  ruby: 'Rubínový rám',   legendary: 'Legendární rám',
    };
    frameHtml = `
      <div class="crys-active-effect">
        🖼 <strong>Rám portrétu:</strong> ${esc(FRAME_LABELS[d.portrait_frame] || d.portrait_frame)}
        <button class="btn btn-sm crys-reset-btn" onclick="resetPortraitFrame()">✕ Odstranit</button>
      </div>`;
  }

  const activeEffectsHtml = (boostHtml || nameColorHtml || frameHtml)
    ? `<div class="crys-active-section">
        <div class="crys-section-title">⚡ Aktivní efekty</div>
        ${boostHtml}${nameColorHtml}${frameHtml}
       </div>`
    : '';

  // Skupiny položek
  const GROUPS = [
    { type: 'consumable',    label: '⚡ Spotřební',       desc: 'Časově omezené bonusy' },
    { type: 'name_color',    label: '🎨 Barvy jména',      desc: 'Cosmetic — pouze vizuální' },
    { type: 'portrait_frame',label: '🖼 Rámy portrétu',   desc: 'Cosmetic — pouze vizuální' },
  ];

  const groupsHtml = GROUPS.map(g => {
    const items = (d.items || []).filter(i => i.type === g.type);
    if (!items.length) return '';
    return `
      <div class="crys-group">
        <div class="crys-group-title">${g.label}</div>
        <div class="crys-group-desc">${g.desc}</div>
        <div class="crys-grid">
          ${items.map(item => _crystalItemCard(item, d.crystals)).join('')}
        </div>
      </div>`;
  }).join('');

  // Login streak widget
  const streak = d.login_streak || 0;
  const sn = d.streak_next || { days: 7, amount: 20, type: 'weekly' };
  const streakPct = sn.type === 'monthly'
    ? Math.round(((30 - sn.days) / 30) * 100)
    : Math.round(((7  - sn.days) / 7)  * 100);
  const streakHtml = `
    <div class="crys-streak-card">
      <div class="crys-streak-title">🔥 Login Streak</div>
      <div class="crys-streak-days">${streak} <span class="crys-streak-lbl">dní v řadě</span></div>
      <div class="crys-streak-bar-wrap">
        <div class="crys-streak-bar" style="width:${streakPct}%"></div>
      </div>
      <div class="crys-streak-next">
        Dalších <strong>${sn.days} dní</strong> → <strong>+${sn.amount} 💎</strong>
        <span class="crys-streak-type">(${sn.type === 'monthly' ? 'měsíční' : 'týdenní'})</span>
      </div>
    </div>`;

  // Zdroje crystalů
  const earnHtml = `
    <div class="crys-earn-section">
      <div class="crys-section-title">💎 Jak získat Crystaly</div>
      <div class="crys-earn-grid">
        <div class="crys-earn-row"><span>🏅 Sezónní pass (tiery 2, 4, 6, 8, 10)</span><span class="crys-earn-amt">+405 💎 max</span></div>
        <div class="crys-earn-row"><span>⚔️ Achievement chainy (5 chainů)</span><span class="crys-earn-amt">+90 💎 celkem</span></div>
        <div class="crys-earn-row"><span>🌍 World Events (komunální)</span><span class="crys-earn-amt">+50–100 💎</span></div>
        <div class="crys-earn-row"><span>⚜️ Guild War výhry (+25 💎 každému)</span><span class="crys-earn-amt">neomezeno</span></div>
        <div class="crys-earn-row"><span>🔥 Login Streak (7 dní: +20, 30 dní: +50)</span><span class="crys-earn-amt">~50 💎/měsíc</span></div>
        <div class="crys-earn-row"><span>🏆 Prestige (za každý level)</span><span class="crys-earn-amt">+150 💎</span></div>
      </div>
      <div class="crys-earn-note">💡 Crystaly jsou <strong>výhradně earned</strong> — žádné P2W. Použití: vzhled a QoL.</div>
    </div>`;

  el.innerHTML = `
    <div class="crys-header">
      <div class="crys-header-title">💎 Crystal Shop</div>
      <div class="crys-balance">
        <span class="crys-balance-ico">💎</span>
        <span class="crys-balance-val">${(d.crystals || 0).toLocaleString('cs')}</span>
        <span class="crys-balance-lbl">krystalů</span>
      </div>
    </div>
    ${activeEffectsHtml}
    ${streakHtml}
    ${groupsHtml}
    ${earnHtml}`;
}

function _crystalItemCard(item, balance) {
  const canAfford = balance >= item.cost;
  const isOwned   = item.owned === true;
  const isActive  = item.active === true;

  let badgeHtml = '';
  if (isOwned || isActive) {
    badgeHtml = `<div class="crys-item-badge">${isActive ? '✓ Aktivní' : '✓ Vlastněno'}</div>`;
  }

  let previewHtml = '';
  if (item.type === 'name_color' && item.color) {
    previewHtml = `<div class="crys-name-preview" style="color:${item.color}">${char?.name || 'Ukázka'}</div>`;
  } else if (item.type === 'portrait_frame') {
    const FRM_C = {
      bronze: '#cd7f32', silver: '#c0c0c0', gold: '#ffd700',
      arcane: '#8b5cf6', ruby: '#dc143c',   legendary: '#ffd700',
    };
    const fc = FRM_C[item.frame] || '#888';
    previewHtml = `<div class="crys-frame-preview pf-${item.frame}" style="border-color:${fc};box-shadow:0 0 10px ${fc}99">🧙</div>`;
  }

  return `
    <div class="crys-item-card ${isOwned || isActive ? 'crys-item-owned' : ''}">
      ${badgeHtml}
      <div class="crys-item-emoji">${item.emoji}</div>
      <div class="crys-item-name">${esc(item.name)}</div>
      <div class="crys-item-desc">${esc(item.description)}</div>
      ${previewHtml}
      <div class="crys-item-footer">
        <span class="crys-item-cost">💎 ${item.cost}</span>
        <button class="btn crys-buy-btn ${canAfford ? '' : 'crys-buy-disabled'}"
          ${canAfford ? `onclick="buyCrystalItem('${item.key}',${item.cost},'${esc(item.name).replace(/'/g,"\\'")}')"`  : 'disabled'}
        >${isOwned || isActive ? '🔄 Koupit znovu' : '🛒 Koupit'}</button>
      </div>
    </div>`;
}

async function buyCrystalItem(key, cost, name) {
  try {
    const d = await api('POST', `/crystals/buy/${key}`);
    toast(d.message, 's', 4000);
    updateUI(d.character);
    await loadCrystals();
  } catch(e) { toast(e.message, 'e'); }
}

async function resetNameColor() {
  try {
    const d = await api('POST', '/crystals/reset-name-color');
    toast(d.message, 's');
    updateUI(d.character);
    await loadCrystals();
  } catch(e) { toast(e.message, 'e'); }
}

async function resetPortraitFrame() {
  try {
    const d = await api('POST', '/crystals/reset-frame');
    toast(d.message, 's');
    updateUI(d.character);
    await loadCrystals();
  } catch(e) { toast(e.message, 'e'); }
}
