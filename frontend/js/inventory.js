// ── INVENTÁŘ ──────────────────────────────────────────────────────────────
const _RARITY_ORDER = {set:0, legendary:1, epic:2, rare:3, uncommon:4, common:5};
const _TYPE_ORDER   = {weapon:0, helmet:1, armor:2, gloves:3, boots:4, ring:5, amulet:6, potion:7};

async function loadInventory() {
  try {
    const d = await api('GET', '/inventory/');
    invData = d.items;
    renderInv();
  } catch(e) { toast(e.message, 'e'); }
}

function filterInv(filter, btn) {
  invFilter = filter;
  document.querySelectorAll('.inv-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderInv();
}

function sortInv(val) {
  invSort = val;
  renderInv();
}

function renderEquipStrip() {
  const strip = document.getElementById('inv-equip-strip');
  if (!strip) return;
  const slots = ['weapon','helmet','armor','gloves','boots','ring','amulet'];
  const eq = char?.equipment || {};
  strip.innerHTML = slots.map(s => {
    const item = eq[s];
    const rc = item ? (RARITY_COL[item.rarity] || '#9d9d9d') : 'var(--border)';
    const invItem = item ? invData.find(i => i.equipped && i.item?.type === s) : null;
    const dur = invItem ? (invItem.durability ?? 100) : null;
    const durCol = dur === null ? '' : dur >= 50 ? '#1eff00' : dur >= 25 ? '#ff8c00' : '#ff4040';
    const durWarning = dur !== null && dur < 25 ? ' inv-strip-slot-crit' : dur !== null && dur < 50 ? ' inv-strip-slot-warn' : '';
    return `<div class="inv-strip-slot${item ? ' inv-strip-slot-filled' : ' inv-strip-slot-empty'}${durWarning}"
               style="--rc:${rc}"
               data-slot="${s}"
               ${invItem ? `onclick="openItemDetail(${JSON.stringify(invItem).replace(/"/g,'&quot;')})"` : ''}>
      <div class="inv-strip-icon">${item ? item.icon : SLOT_ICONS[s]}</div>
      <div class="inv-strip-name" style="color:${rc}">${item ? esc(item.name) : SLOT_CZ[s]}</div>
      ${dur !== null
        ? `<div class="inv-strip-dur"><div class="inv-strip-dur-fill" style="width:${dur}%;background:${durCol}"></div></div>`
        : `<div class="inv-strip-dur inv-strip-dur-empty"></div>`}
    </div>`;
  }).join('');
}

function _sortedInv(items) {
  const copy = [...items];
  if (invSort === 'rarity')      copy.sort((a,b) => (_RARITY_ORDER[a.item?.rarity]??9) - (_RARITY_ORDER[b.item?.rarity]??9));
  else if (invSort === 'type')   copy.sort((a,b) => (_TYPE_ORDER[a.item?.type]??9) - (_TYPE_ORDER[b.item?.type]??9) || (a.item?.name||'').localeCompare(b.item?.name||'', 'cs'));
  else if (invSort === 'name')   copy.sort((a,b) => (a.item?.name||'').localeCompare(b.item?.name||'', 'cs'));
  else if (invSort === 'durability') copy.sort((a,b) => (a.durability??100) - (b.durability??100));
  return copy;
}

function renderInv() {
  renderEquipStrip();

  const other = ['gloves','boots','ring','amulet'];
  let filtered = invFilter === 'all'   ? invData
    : invFilter === 'other' ? invData.filter(i => other.includes(i.item?.type))
    : invFilter === 'set'   ? invData.filter(i => i.item?.rarity === 'set')
    : invData.filter(i => i.item?.type === invFilter);
  filtered = _sortedInv(filtered);

  const bagCount = invData.filter(i => !i.equipped).length;
  const bagLabel = document.getElementById('inv-bag-label');
  if (bagLabel) bagLabel.textContent = `BATOH (${bagCount})`;
  set('inv-count', `${filtered.length} itemů`);

  const grid = document.getElementById('inv-grid');
  if (!filtered.length) {
    const isAll = invFilter === 'all';
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🎒</div>
        <div class="empty-state-title">${isAll ? 'Žádné předměty.' : 'Žádné předměty tohoto typu.'}</div>
        <div class="empty-state-hint">${isAll ? 'Získej je z questů nebo obchodu.' : 'Zkus jiný filtr nebo doplň inventář.'}</div>
      </div>`;
    return;
  }

  const UPGRADE_BADGE = ['','★','★★','★★★'];
  grid.innerHTML = filtered.map(inv => {
    const item = inv.item;
    const isSet = item?.rarity === 'set';
    const rc = RARITY_COL[item?.rarity] || '#9d9d9d';
    const bonuses = Object.entries(item?.bonuses || {}).filter(([,v]) => v > 0);
    const bonusTxt = bonuses.slice(0,2).map(([k,v]) => `+${v} ${k.toUpperCase()}`).join(' · ');
    const ul = inv.upgrade_level || 0;
    const equippable = ['weapon','helmet','armor','gloves','boots','ring','amulet'].includes(item?.type);
    const dur = inv.durability ?? 100;
    const durCol = dur >= 50 ? '#1eff00' : dur >= 25 ? '#ff8c00' : '#ff4040';
    const durBar = equippable ? `<div class="inv-dur-bar"><div class="inv-dur-fill" style="width:${dur}%;background:${durCol}"></div></div>` : '';
    return `<div class="inv-card ${inv.equipped?'equipped':''} ${isSet?'inv-card-set':''}" style="--rc:${rc}"
              onclick="openItemDetail(${JSON.stringify(inv).replace(/"/g,'&quot;')})">
      ${isSet ? `<div class="inv-set-glow"></div>` : ''}
      <div class="inv-card-icon">${item?.icon || '📦'}</div>
      <div class="inv-card-name" style="color:${rc}">${esc(item?.name||'?')}</div>
      <div class="inv-card-type">${esc(SLOT_CZ[item?.type] || item?.type || '')}</div>
      ${isSet ? `<div class="inv-set-badge">✦ ${esc(item.set_name||'Set')}</div>` : `<div class="inv-card-bonus">${bonusTxt}</div>`}
      ${durBar}
      ${ul > 0 ? `<div class="inv-upgrade-badge">${UPGRADE_BADGE[ul]}</div>` : ''}
      ${inv.quantity > 1 ? `<div class="inv-card-qty">×${inv.quantity}</div>` : ''}
      ${inv.equipped ? '<div class="inv-card-equipped-badge">NASAZENO</div>' : ''}
    </div>`;
  }).join('');
}

// ── ITEM DETAIL MODAL ─────────────────────────────────────────────────────
function openItemDetail(inv) {
  const item = inv.item;
  if (!item) return;
  const rc = RARITY_COL[item.rarity] || '#9d9d9d';
  const bonuses = Object.entries(item.bonuses || {}).filter(([,v]) => v > 0);
  const equippable = ['weapon','helmet','armor','gloves','boots','ring','amulet'].includes(item.type);
  const bonusLabels = {atk:'Útok',def:'Obrana',spd:'Rychlost',hp:'Max HP',mp:'XP (při použití)',str:'Síla',dex:'Obratnost',int:'Inteligence',end:'Výdrž',luck:'Štěstí'};
  const isPotion = item.type === 'potion';

  const bonusRows = bonuses.map(([k,v]) =>
    `<div class="item-bonus-row"><span class="item-bonus-lbl">${bonusLabels[k]||k}</span><span class="item-bonus-val">+${v}</span></div>`
  ).join('');

  const ul = inv.upgrade_level || 0;
  const dur = inv.durability ?? 100;
  const REPAIR_COST_PER_PT = 3;
  const repairCost = Math.max(0, (100 - dur) * REPAIR_COST_PER_PT);
  const durCol  = dur >= 50 ? '#1eff00' : dur >= 25 ? '#ff8c00' : '#ff4040';
  const durLabel = dur >= 75 ? 'Výborná' : dur >= 50 ? 'Dobrá' : dur >= 25 ? 'Poškozená' : 'Kritická';
  const durHtml = equippable ? `
    <div class="item-dur-section">
      <div class="item-dur-header">
        <span>Trvanlivost: <strong style="color:${durCol}">${durLabel} (${dur}/100)</strong></span>
        ${dur < 100 ? `<span style="color:var(--text3);font-size:.7rem">Oprava: ${repairCost} G</span>` : ''}
      </div>
      <div class="item-dur-bar"><div class="item-dur-fill" style="width:${dur}%;background:${durCol}"></div></div>
    </div>` : '';
  const UPGRADE_COSTS_JS = {0:500, 1:2000, 2:8000};
  const UPGRADE_RARITY = ['common','uncommon','rare','epic'];
  const UPGRADE_BADGE_JS = ['','★','★★','★★★'];
  const canUpgrade = equippable && !['epic','legendary','set'].includes(item.rarity) && ul < 3 && inv.id !== -1;
  const upgradeCost = UPGRADE_COSTS_JS[ul];
  const baseRarityIdx = UPGRADE_RARITY.indexOf(item.rarity);
  const nextRarity = baseRarityIdx >= 0 ? UPGRADE_RARITY[Math.min(baseRarityIdx + ul + 1, 3)] : null;
  const RARITY_CZ_UP = {common:'Běžný',uncommon:'Neobvyklý',rare:'Vzácný',epic:'Epický'};
  const upgradeHtml = canUpgrade ? `
    <div class="upgrade-preview">
      <div class="upgrade-preview-title">⬆ Vylepšení</div>
      <div class="upgrade-preview-info">
        ${ul > 0 ? `<span class="upgrade-badge-sm">${UPGRADE_BADGE_JS[ul]}</span>` : ''}
        <span style="color:var(--text2)">${item.rarity} → </span>
        <span style="color:${RARITY_COL[nextRarity]||'#fff'};font-weight:700">${RARITY_CZ_UP[nextRarity]||nextRarity}</span>
        <span style="color:var(--text3);margin-left:8px">+35–40% bonusů</span>
      </div>
      <div class="upgrade-preview-cost">Cena: <strong style="color:var(--gold2)">${upgradeCost.toLocaleString('cs')} G</strong>
        <span style="color:var(--text3);font-size:.7rem;margin-left:6px">(Máš: ${(char?.gold||0).toLocaleString('cs')} G)</span>
      </div>
    </div>` : (ul >= 3 ? `<div class="upgrade-preview upgrade-maxed">✦ Maximálně vylepšeno (★★★)</div>` : '');

  const currentItem = (equippable && !inv.equipped && char?.equipment) ? char.equipment[item.type] : null;
  let compHtml = '';
  if (currentItem && currentItem.id !== item.id) {
    const curRc = RARITY_COL[currentItem.rarity] || '#9d9d9d';
    const allKeys = Object.keys(item.bonuses || {});
    const compRows = allKeys.map(k => {
      const nv = (item.bonuses[k] || 0);
      const cv = (currentItem.bonuses?.[k] || 0);
      if (nv === 0 && cv === 0) return '';
      const diff = nv - cv;
      const dc = diff > 0 ? 'var(--green2)' : diff < 0 ? 'var(--accent2)' : 'var(--text3)';
      const dt = diff > 0 ? `▲+${diff}` : diff < 0 ? `▼${diff}` : '=';
      return `<div style="display:grid;grid-template-columns:1fr 2.5rem 3rem 2.5rem;gap:2px 6px;align-items:center;padding:2px 0;font-size:.74rem">
        <span style="color:var(--text2)">${bonusLabels[k]||k}</span>
        <span style="text-align:right;color:var(--text3)">${cv}</span>
        <span style="text-align:center;font-weight:700;color:${dc}">${dt}</span>
        <span style="text-align:right;color:var(--text)">${nv}</span>
      </div>`;
    }).filter(Boolean).join('');
    compHtml = `
      <div style="background:var(--panel2);border:1px solid var(--border);border-radius:4px;padding:10px;margin-bottom:10px">
        <div style="font-family:'Cinzel',serif;font-size:.6rem;letter-spacing:1px;text-transform:uppercase;color:var(--text2);margin-bottom:6px">⚖ Porovnání s nasazeným</div>
        <div style="font-size:.78rem;color:${curRc};margin-bottom:6px">${currentItem.icon} ${esc(currentItem.name)}</div>
        <div style="font-family:'Cinzel',serif;font-size:.58rem;display:grid;grid-template-columns:1fr 2.5rem 3rem 2.5rem;gap:0 6px;color:var(--text3);margin-bottom:4px;padding-bottom:3px;border-bottom:1px solid rgba(255,255,255,.05)">
          <span></span><span style="text-align:right">Stav</span><span style="text-align:center">Rozdíl</span><span style="text-align:right">Nový</span>
        </div>
        ${compRows || '<span style="color:var(--text3);font-size:.74rem">Žádné bonusy k porovnání</span>'}
      </div>`;
  }

  // Zjisti kolik kusů sady hráč má nasazeno (pro set itemy)
  let setInfoHtml = '';
  if (item.rarity === 'set' && item.set_name && char?.set_bonuses?.active) {
    const sb = Object.values(char.set_bonuses.active).find(s => s.set_name === item.set_name);
    const pieces = sb?.pieces_equipped ?? 0;
    const b3 = sb?.bonus_3pc_active;
    const b5 = sb?.bonus_5pc_active;
    const need3 = Math.max(0, 3 - pieces);
    const need5 = Math.max(0, 5 - pieces);
    setInfoHtml = `
      <div class="set-info-box" style="--set-color:${rc}">
        <div class="set-info-title">✦ ${esc(item.set_name)}</div>
        <div class="set-info-pieces">${pieces} / 5 kusů nasazeno</div>
        <div class="set-bonus-row ${b3?'set-bonus-active':'set-bonus-inactive'}">
          <span class="set-bonus-req">3 kusy:</span>
          <span>${esc(sb?.bonus_3pc_desc ?? '+15% HP')}</span>
          ${b3 ? '<span class="set-bonus-check">✓</span>' : `<span class="set-bonus-need">ještě ${need3}</span>`}
        </div>
        <div class="set-bonus-row ${b5?'set-bonus-active':'set-bonus-inactive'}">
          <span class="set-bonus-req">5 kusů:</span>
          <span>${esc(sb?.bonus_5pc_desc ?? 'Bonus')}</span>
          ${b5 ? '<span class="set-bonus-check">✓</span>' : `<span class="set-bonus-need">ještě ${need5}</span>`}
        </div>
      </div>`;
  }

  document.getElementById('modal-item-body').innerHTML = `
    <div class="item-detail-header ${item.rarity === 'set' ? 'item-detail-header-set' : ''}" style="--set-color:${rc}">
      <div class="item-detail-icon">${item.icon}</div>
      <div class="item-detail-info">
        <div class="item-detail-name" style="color:${rc}">${esc(item.name)}${ul > 0 ? ` <span class="upgrade-badge-title">${UPGRADE_BADGE_JS[ul]}</span>` : ''}</div>
        <div class="item-detail-meta">
          <span style="color:${rc}">${RARITY_CZ[item.rarity]||item.rarity}</span>
          <span style="color:var(--text2)">·</span>
          <span style="color:var(--text2)">${SLOT_CZ[item.type]||item.type}</span>
          <span style="color:var(--text2)">·</span>
          <span style="color:var(--text2)">Min. Lv.${item.min_level}</span>
        </div>
      </div>
    </div>
    ${setInfoHtml}
    ${item.description ? `<div class="item-desc">${esc(item.description)}</div>` : ''}
    ${bonusRows ? `<div class="item-bonuses">${bonusRows}</div>` : ''}
    ${durHtml}
    ${upgradeHtml}
    ${compHtml}
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;font-size:.8rem;color:var(--text2)">
      <span>Počet: <strong style="color:var(--text)">${inv.quantity} ks</strong></span>
      <span>Hodnota: <strong style="color:var(--gold2)">${item.sell_price} G / ks</strong></span>
    </div>
    <div class="item-actions">
      ${isPotion && inv.id !== -1 ? `<button class="btn btn-green" onclick="useItem(${inv.id},'${esc(item.name).replace(/'/g,"\\'")}')">🧪 Použít</button>` : ''}
      ${equippable && !inv.equipped ? `<button class="btn btn-gold" onclick="equipItem(${inv.id});closeModal('modal-item')">⚔ Nasadit</button>` : ''}
      ${inv.equipped ? `<button class="btn" onclick="unequipSlot('${item.type}');closeModal('modal-item')">🔓 Sundat</button>` : ''}
      ${canUpgrade ? `<button class="btn btn-upgrade" onclick="upgradeItem(${inv.id})">⬆ Vylepšit (${upgradeCost.toLocaleString('cs')} G)</button>` : ''}
      ${equippable && dur < 100 && inv.id !== -1 ? `<button class="btn btn-repair" onclick="repairItem(${inv.id},${repairCost})">🔧 Opravit (${repairCost} G)</button>` : ''}
      ${inv.id !== -1 && !isPotion ? `<button class="btn" onclick="prepareSell(${JSON.stringify(inv).replace(/"/g,'&quot;')});closeModal('modal-item');showPage('market')" style="background:linear-gradient(135deg,#5a3800,#a06808,#5a3800);border-color:var(--gold2)">📤 Prodat na trhu</button>` : ''}
      ${inv.id !== -1 ? `<button class="btn btn-sm" style="background:rgba(180,30,30,.2);border-color:var(--accent);color:var(--accent2)" onclick="sellToShop(${inv.id},${item.sell_price});closeModal('modal-item')">🪙 Prodat (${item.sell_price}G)</button>` : ''}
    </div>`;

  openModal('modal-item');
}

async function equipItem(invId) {
  const invItem = invData.find(i => i.id === invId);
  const itemName = invItem?.item?.name || 'item';
  try {
    const d = await api('POST', '/inventory/equip', { inv_item_id: invId });
    toast(d.message, 's', 2500);
    updateUI(d.character);
    const slotEl = document.querySelector(`.inv-strip-slot[data-slot="${invItem?.item?.type}"]`);
    if (slotEl) { slotEl.classList.remove('inv-strip-slot-warn','inv-strip-slot-crit'); slotEl.classList.add('slot-accept'); setTimeout(() => slotEl.classList.remove('slot-accept'), 520); }
    renderEquip();
    await loadInventory();
    addAct(`⚔ Nasazeno: ${itemName}`);
  } catch(e) { toast(e.message, 'e'); }
}

async function sellToShop(invId, price) {
  try {
    const d = await api('POST', '/inventory/sell', { inv_item_id: invId, quantity: 1 });
    toast(d.message, 's');
    addAct(`🪙 Prodáno do shopu za ${d.gold_earned} G`);
    await refreshChar();
    await loadInventory();
  } catch(e) { toast(e.message, 'e'); }
}

async function upgradeItem(invId) {
  try {
    const d = await api('POST', `/inventory/upgrade/${invId}`);
    toast(d.message, 's', 4000);
    addAct(`⬆ Upgrade: ${d.inv_item?.item?.name || '?'} → ${d.new_rarity}`);
    updateUI(d.character);
    closeModal('modal-item');
    renderEquip();
    await loadInventory();
  } catch(e) { toast(e.message, 'e'); }
}

async function repairItem(invId, cost) {
  try {
    const d = await api('POST', `/inventory/repair/${invId}`);
    toast(d.message, 's', 3000);
    updateUI(d.character);
    closeModal('modal-item');
    renderEquip();
    await loadInventory();
  } catch(e) { toast(e.message, 'e'); }
}

async function repairAll() {
  try {
    const d = await api('POST', '/inventory/repair');
    toast(d.message, 's', 3000);
    addAct(`🔧 Opraveno vybavení za ${d.total_cost} G`);
    updateUI(d.character);
    renderEquip();
    await loadInventory();
  } catch(e) { toast(e.message, 'e'); }
}
