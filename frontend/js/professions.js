// ── PROFESE v3 ─────────────────────────────────────────────────────────────
// Enchanter / Alchymista / Kovář — choose-once, rank 0–5

const PROF_V3 = {
  enchanter:  { name: 'Enchanter',  icon: '⚗',  color: '#e8b020', dim: 'rgba(232,176,32,.10)' },
  alchymista: { name: 'Alchymista', icon: '🧪', color: '#40c870', dim: 'rgba(64,200,112,.10)'  },
  blacksmith: { name: 'Kovář',      icon: '⚒',  color: '#e06030', dim: 'rgba(224,96,48,.10)'   },
};

const PROF_RANK_NAMES = ['Novic', 'Učedník', 'Tovaryš', 'Expert', 'Mistr', 'Velmistr'];

const PROF_ACTIONS = {
  enchanter:  ['enchant', 'disenchant', 'craft_scroll'],
  alchymista: ['brew', 'dissolve'],
  blacksmith: ['destroy', 'upgrade'],
};

const PROF_ACTION_LABELS = {
  enchant:      'Enchant',
  disenchant:   'Disenchant',
  craft_scroll: 'Craft Scroll',
  brew:         'Brew',
  dissolve:     'Dissolve',
  destroy:      'Destroy',
  upgrade:      'Upgrade',
};

const EQUIP_SLOT_TYPES = new Set(['weapon','armor','helmet','gloves','boots','ring','amulet']);

let _profDataV3    = null;
let _profRecipes   = null;
let _profActiveTab = 'enchant';
let _profSelectedItem = null;

// ── LOAD ────────────────────────────────────────────────────────────────────

async function loadProfessions() {
  const wrap = document.getElementById('prof-content');
  if (!wrap) return;
  if (!char) {
    wrap.innerHTML = '<div class="pr-loading">Nejdřív si vytvoř postavu.</div>';
    return;
  }
  wrap.innerHTML = '<div class="pr-loading">Načítám profesi...</div>';
  try {
    if (typeof loadInventory === 'function') await loadInventory();
    _profDataV3 = await api('GET', '/professions/');
    if (_profDataV3.has_profession) {
      _profRecipes = await api('GET', '/professions/recipes');
      const key = _profDataV3.current?.profession_key;
      if (key && PROF_ACTIONS[key]) _profActiveTab = PROF_ACTIONS[key][0];
    }
    _renderProfPage(wrap);
  } catch(e) {
    wrap.innerHTML = `<div class="pr-error">⚠ ${esc(e.message)}</div>`;
  }
}

function _renderProfPage(wrap) {
  if (!_profDataV3.has_profession) {
    _renderProfChoice(wrap);
  } else {
    _renderProfDetail(wrap, _profDataV3.current);
  }
}

// ── VÝBĚR PROFESE ────────────────────────────────────────────────────────────

function _renderProfChoice(wrap) {
  const cards = (_profDataV3.professions || []).map(p => {
    const meta = PROF_V3[p.profession_key] || {};
    return `
      <div class="pr-card" style="--pcol:${meta.color};--pdim:${meta.dim}">
        <div class="pr-card-header">
          <div class="pr-card-ico">${esc(p.icon)}</div>
          <div style="flex:1;min-width:0">
            <div class="pr-card-name">${esc(p.name)}</div>
          </div>
        </div>
        <div class="pr-card-desc">${esc(p.description)}</div>
        <button class="pr-action-btn pr-action-activate btn-full" style="margin-top:10px"
          onclick="chooseProfession('${p.profession_key}')">
          Zvolit ${esc(p.name)}
        </button>
      </div>`;
  }).join('');

  wrap.innerHTML = `
    <div class="pr-hint">
      ⚠ Profesi lze zvolit <strong>pouze jednou</strong>. Tato volba je <strong>trvalá</strong>.
    </div>
    <div class="pr-hero" style="margin-bottom:18px">
      <div class="pr-hero-inner">
        <div class="pr-hero-icon">⚗</div>
        <div class="pr-hero-title">Zvol svou Profesi</div>
        <div class="pr-hero-sub">Každá profese ti dává unikátní schopnosti. Vyber moudře — nelze změnit.</div>
      </div>
    </div>
    <div class="pr-grid">${cards}</div>`;
}

async function chooseProfession(key) {
  const meta = PROF_V3[key] || { name: key };
  if (!confirm(`Opravdu chceš zvolit profesi „${meta.name}"?\n\nTato volba je TRVALÁ a nelze ji změnit.`)) return;
  try {
    const res = await api('POST', '/professions/choose', { profession_key: key });
    toast(res.message || 'Profese zvolena!', 's');
    await loadProfessions();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── DETAIL ZVOLENOU PROFESE ──────────────────────────────────────────────────

function _renderProfDetail(wrap, prof) {
  // Levý sidebar — všechny 3 profese
  const allProfs = _profDataV3.professions || [];
  const sidebarHtml = allProfs.map(p => {
    const pmeta   = PROF_V3[p.profession_key] || {};
    const isChosen = p.profession_key === prof.profession_key;
    return `
      <div class="pr-sidebar-item ${isChosen ? 'is-active' : 'is-locked'}" style="--pcol:${pmeta.color || '#888'}">
        <span class="pr-sidebar-ico">${esc(p.icon)}</span>
        <span class="pr-sidebar-name">${esc(p.name)}</span>
        ${isChosen ? '<span class="pr-sidebar-check">✓</span>' : ''}
      </div>`;
  }).join('');

  wrap.innerHTML = `
    <div class="pr-panel-layout">
      <div class="pr-sidebar">${sidebarHtml}</div>
      <div class="pr-main-panel" id="prof-main-panel"></div>
    </div>`;

  _fillMainPanel(prof);
}

function _fillMainPanel(prof) {
  const el = document.getElementById('prof-main-panel');
  if (!el) return;

  const meta     = PROF_V3[prof.profession_key] || { name: prof.name, icon: prof.icon, color: '#aaa', dim: 'rgba(170,170,170,.08)' };
  const rank     = prof.rank || 0;
  const rankName = PROF_RANK_NAMES[rank] || 'Novic';
  const xpPct    = prof.xp_to_next ? Math.min(100, Math.round((prof.xp / prof.xp_to_next) * 100)) : 100;
  const stars    = Array.from({length: 5}, (_, i) =>
    `<span class="pr-star" style="color:${i < rank ? meta.color : 'var(--border2)'}">★</span>`
  ).join('');

  const actions  = PROF_ACTIONS[prof.profession_key] || [];
  const tabsHtml = actions.map(a =>
    `<button class="pr-tab ${_profActiveTab === a ? 'active' : ''}"
      onclick="setProfTab('${a}')">${PROF_ACTION_LABELS[a] || a}</button>`
  ).join('');

  el.innerHTML = `
    <div class="pr-detail-banner" style="--pcol:${meta.color};--pdim:${meta.dim}">
      <div class="pr-detail-left">
        <div class="pr-detail-ico">${prof.icon}</div>
        <div class="pr-detail-title-block">
          <div class="pr-detail-name">${esc(prof.name)}</div>
          <div class="pr-rank-row">
            <span class="pr-rank-badge" style="border-color:${meta.color};color:${meta.color}">${rankName}</span>
            <span class="pr-stars">${stars}</span>
          </div>
          <div class="pr-xp-row">
            <div class="pr-xp-track" style="flex:1">
              <div class="pr-xp-fill" style="width:${xpPct}%;background:${meta.color}"></div>
            </div>
            <div class="pr-xp-label">${prof.xp_to_next ? `${prof.xp} / ${prof.xp_to_next} XP` : 'MAX RANK'}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="pr-tabs">${tabsHtml}</div>
    <div id="prof-action-panel" class="pr-sub-content"></div>`;

  _renderActionPanel();
}

function setProfTab(tab) {
  _profActiveTab = tab;
  _profSelectedItem = null;
  if (_profDataV3?.current) _fillMainPanel(_profDataV3.current);
}

function _renderActionPanel() {
  const el = document.getElementById('prof-action-panel');
  if (!el) return;
  // Registrace hover tooltipů — stejný systém jako inventory/equipment
  _registerTipContainer('prof-content', '.inv-card[data-inv-id]', card => {
    const invId = parseInt(card.dataset.invId, 10);
    return invData?.find(i => i.id === invId) || null;
  });
  switch (_profActiveTab) {
    case 'enchant':      el.innerHTML = _tplEnchant();      break;
    case 'disenchant':   el.innerHTML = _tplDisenchant();   break;
    case 'craft_scroll': el.innerHTML = _tplCraftScroll();  break;
    case 'brew':         el.innerHTML = _tplBrew();         break;
    case 'dissolve':     el.innerHTML = _tplDissolve();     break;
    case 'destroy':      el.innerHTML = _tplDestroy();      break;
    case 'upgrade':      el.innerHTML = _tplUpgrade();      break;
    default: el.innerHTML = '';
  }
}

// ── HELPER: item list pro výběr ──────────────────────────────────────────────

function _equipItems() {
  return (invData || []).filter(i => !i.equipped && EQUIP_SLOT_TYPES.has(i.item?.type));
}

function _potionItems() {
  return (invData || []).filter(i =>
    !i.equipped && (i.item?.name?.includes('Potion') || i.item?.name?.includes('Elixir'))
  );
}

function _itemGridHtml(items, gridId) {
  if (!items.length) return `<div class="pr-empty-state"><span>🎒</span><span>Prázdný inventář</span></div>`;
  const BTAG = {atk:'ATK',def:'ARMOR',spd:'SPD',str:'STR',dex:'AQI',int:'INT',end:'HP',luck:'LUCK',hp:'HP',mp:'MP'};
  const cards = items.map(i => {
    const item = i.item;
    const rc = RARITY_COL[item?.rarity] || '#9d9d9d';
    const bonuses = Object.entries(item?.bonuses || {}).filter(([,v]) => v > 0);
    const bonusTxt = bonuses.slice(0,2).map(([k,v]) => `+${v} ${BTAG[k]||k.toUpperCase()}`).join(' · ');
    const equippable = ['weapon','helmet','armor','gloves','boots','ring','amulet'].includes(item?.type);
    const dur = i.durability ?? 100;
    const durCol = dur >= 50 ? '#1eff00' : dur >= 25 ? '#ff8c00' : '#ff4040';
    const durBar = equippable ? `<div class="inv-dur-bar"><div class="inv-dur-fill" style="width:${dur}%;background:${durCol}"></div></div>` : '';
    return `<div class="inv-card" data-inv-id="${i.id}" style="--rc:${rc}" data-rarity="${item?.rarity||''}"
              onclick="selectProfItem(${i.id},'${gridId}')">
      <div class="inv-card-icon">${item?.icon || '📦'}</div>
      <div class="inv-card-name" style="color:${rc}">${esc(item?.name||'?')}</div>
      <div class="inv-card-type">${esc(SLOT_CZ[item?.type] || item?.type || '')}</div>
      <div class="inv-card-bonus">${bonusTxt}</div>
      ${durBar}
      ${i.quantity > 1 ? `<div class="inv-card-qty">×${i.quantity}</div>` : ''}
    </div>`;
  }).join('');
  return `<div class="inv-grid" id="${gridId}">${cards}</div>`;
}

function selectProfItem(invId, gridId) {
  _profSelectedItem = invId;
  const grid = document.getElementById(gridId);
  if (!grid) return;
  grid.querySelectorAll('.inv-card').forEach(c => c.classList.remove('selected'));
  const card = grid.querySelector(`[data-inv-id="${invId}"]`);
  if (card) card.classList.add('selected');
  _updateProfPreview(invId, gridId);
}

function _updateProfPreview(invId, gridId) {
  const previewMap = {
    'prof-dis-item':  'prof-dis-preview',
    'prof-diss-item': 'prof-diss-preview',
    'prof-dest-item': 'prof-dest-preview',
  };
  const previewId = previewMap[gridId];
  if (!previewId) return;
  const el = document.getElementById(previewId);
  if (!el) return;

  const inv = (invData || []).find(i => i.id === invId);
  if (!inv) { el.innerHTML = ''; return; }

  const rank = _profDataV3?.current?.rank || 0;
  let recipe = null;

  if (gridId === 'prof-dis-item') {
    const rarity = inv.override_rarity || inv.item?.rarity;
    recipe = _profRecipes?.recipes?.disenchant?.[rarity];
  } else if (gridId === 'prof-diss-item') {
    recipe = _profRecipes?.recipes?.dissolve?.[inv.item?.name];
  } else if (gridId === 'prof-dest-item') {
    const rarity = inv.override_rarity || inv.item?.rarity;
    recipe = _profRecipes?.recipes?.destroy?.[rarity];
  }

  if (!recipe) {
    el.innerHTML = `<div class="pr-preview-empty">Tento item nelze zpracovat.</div>`;
    return;
  }
  if (rank < (recipe.min_rank || 0)) {
    el.innerHTML = `<div class="pr-preview-locked">🔒 Vyžaduje Rank ${recipe.min_rank}</div>`;
    return;
  }
  const items = Object.entries(recipe.outputs)
    .map(([n, q]) => `<span class="pr-preview-item"><strong>${q}×</strong> ${esc(n)}</span>`)
    .join('');
  el.innerHTML = `<div class="pr-preview-box"><span class="pr-preview-label">Získáš:</span>${items}</div>`;
}

// ── ENCHANT ──────────────────────────────────────────────────────────────────

function _tplEnchant() {
  const rank    = _profDataV3?.current?.rank || 0;
  const recipes = _profRecipes?.recipes;
  const basics  = recipes?.enchant?.basic_effects   || ['atk','def','hp'];
  const sigs    = rank >= 5 ? (recipes?.enchant?.signature_effects || []) : [];
  const allFx   = [...basics, ...sigs];
  const fxLabels = { atk:'ATK +', def:'DEF +', hp:'HP +', lifesteal:'Lifesteal 5%', reflect:'Reflect 5%', crit_bonus:'Crit Bonus 5%' };
  const fxOpts  = allFx.map(f => `<option value="${f}">${fxLabels[f] || f}</option>`).join('');
  const items   = _equipItems();

  return `
    <div class="pr-form-card">
      <div class="pr-form-title">⚗ Enchant</div>
      <div class="pr-hint">Přidá magický efekt na vybraný equipment item.</div>
      <div class="pr-form-row"><label>Item</label>${_itemGridHtml(items, 'prof-ench-item')}</div>
      <div class="pr-form-row"><label>Efekt</label>
        <select id="prof-ench-fx" class="pr-input"><option value="">Vyber efekt</option>${fxOpts}</select>
      </div>
      <button class="btn btn-gold btn-full" style="margin-top:10px" onclick="doEnchant()">⚗ Enchant</button>
    </div>`;
}

async function doEnchant() {
  const itemId = _profSelectedItem;
  const effect = document.getElementById('prof-ench-fx')?.value;
  if (!itemId) { toast('Vyber item.', 'e'); return; }
  if (!effect) { toast('Vyber efekt.', 'e'); return; }
  try {
    const res = await api('POST', '/professions/enchant', { inventory_item_id: itemId, effect });
    toast(res.message || 'Enchant aplikován!', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── DISENCHANT ───────────────────────────────────────────────────────────────

function _tplDisenchant() {
  const items = _equipItems();
  return `
    <div class="pr-form-card">
      <div class="pr-form-title">💥 Disenchant</div>
      <div class="pr-hint">Rozloží item na reagenty (Arcane Dust / Enchanted Shard / Void Crystal). Item bude <strong>zničen</strong>.</div>
      <div class="pr-form-row"><label>Item</label>${_itemGridHtml(items, 'prof-dis-item')}</div>
      <div id="prof-dis-preview" class="pr-preview"></div>
      <button class="btn btn-red btn-full" style="margin-top:10px" onclick="doDisenchant()">💥 Disenchant</button>
    </div>`;
}

async function doDisenchant() {
  const itemId = _profSelectedItem;
  if (!itemId) { toast('Vyber item.', 'e'); return; }
  try {
    const res = await api('POST', '/professions/disenchant', { inventory_item_id: itemId });
    toast(res.message || 'Disenchant dokončen!', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── CRAFT SCROLL ─────────────────────────────────────────────────────────────

function _tplCraftScroll() {
  const rank = _profDataV3?.current?.rank || 0;
  const recipes = _profRecipes?.recipes;
  const cost = recipes?.enchant?.craft_scroll_cost || {};
  const costStr = Object.entries(cost).map(([k,v]) => `${v}× ${k}`).join(', ');
  const locked = rank < 5;
  return `
    <div class="pr-form-card">
      <div class="pr-form-title">📜 Craft Scroll</div>
      ${locked
        ? '<div class="pr-locked-notice">🔒 Vyžaduje Rank 5 (Velmistr).</div>'
        : `<div class="pr-hint">Vyrobí Enchant Scroll pro trh.<br>Cena: <strong>${esc(costStr)}</strong></div>
           <button class="btn btn-gold btn-full" style="margin-top:10px" onclick="doCraftScroll()">📜 Craft Scroll</button>`
      }
    </div>`;
}

async function doCraftScroll() {
  try {
    const res = await api('POST', '/professions/craft-scroll');
    toast(res.message || 'Scroll vyroben!', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── BREW ─────────────────────────────────────────────────────────────────────

function _tplBrew() {
  const rank    = _profDataV3?.current?.rank || 0;
  const recipes = _profRecipes?.recipes?.brew || {};

  const cards = Object.entries(recipes).map(([name, r]) => {
    const locked = rank < (r.min_rank || 1);
    const costStr = Object.entries(r.cost || {}).map(([k,v]) => `${v}× ${k}`).join(', ');
    return `
      <div class="pr-form-card ${locked ? 'pr-form-dark' : ''}" style="margin-bottom:10px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
          <div>
            <div class="pr-form-title" style="margin-bottom:4px">🧪 ${esc(name)}</div>
            <div style="font-size:0.76rem;color:var(--text3)">Cena: ${esc(costStr)}</div>
            ${locked ? `<div style="font-size:0.72rem;color:var(--accent2);margin-top:3px">🔒 Rank ${r.min_rank}</div>` : ''}
          </div>
          <button class="btn btn-green" ${locked ? 'disabled' : ''}
            onclick="doBrew(${JSON.stringify(name)})">Brew</button>
        </div>
      </div>`;
  }).join('');

  return cards || '<div class="pr-empty-state"><span>🧪</span><span>Žádné recepty</span></div>';
}

async function doBrew(recipe) {
  try {
    const res = await api('POST', '/professions/brew', { recipe });
    toast(res.message || `${recipe} vyroben!`, 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── DISSOLVE ─────────────────────────────────────────────────────────────────

function _tplDissolve() {
  const items = _potionItems();
  return `
    <div class="pr-form-card">
      <div class="pr-form-title">⚗ Dissolve</div>
      <div class="pr-hint">Rozloží lektvar na reagenty. Lektvar bude <strong>spotřebován</strong>.</div>
      <div class="pr-form-row"><label>Lektvar</label>${_itemGridHtml(items, 'prof-diss-item')}</div>
      <div id="prof-diss-preview" class="pr-preview"></div>
      <button class="btn btn-red btn-full" style="margin-top:10px" onclick="doDissolve()">⚗ Dissolve</button>
    </div>`;
}

async function doDissolve() {
  const itemId = _profSelectedItem;
  if (!itemId) { toast('Vyber lektvar.', 'e'); return; }
  try {
    const res = await api('POST', '/professions/dissolve', { inventory_item_id: itemId });
    toast(res.message || 'Dissolve dokončen!', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── DESTROY ──────────────────────────────────────────────────────────────────

function _tplDestroy() {
  const items = _equipItems();
  return `
    <div class="pr-form-card">
      <div class="pr-form-title">🔨 Destroy</div>
      <div class="pr-hint">Zničí item a vrátí kovové materiály (Metal Scraps / Refined Ore / Soulsteel Fragment).</div>
      <div class="pr-form-row"><label>Item</label>${_itemGridHtml(items, 'prof-dest-item')}</div>
      <div id="prof-dest-preview" class="pr-preview"></div>
      <button class="btn btn-red btn-full" style="margin-top:10px" onclick="doDestroy()">🔨 Destroy</button>
    </div>`;
}

async function doDestroy() {
  const itemId = _profSelectedItem;
  if (!itemId) { toast('Vyber item.', 'e'); return; }
  try {
    const res = await api('POST', '/professions/destroy', { inventory_item_id: itemId });
    toast(res.message || 'Item zničen.', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── UPGRADE ──────────────────────────────────────────────────────────────────

function _tplUpgrade() {
  const rank    = _profDataV3?.current?.rank || 0;
  const recipes = _profRecipes?.recipes?.upgrade || {};
  const items   = _equipItems();

  const table = Object.entries(recipes).map(([rarity, r]) => {
    const locked   = rank < (r.min_rank || 1);
    const costStr  = Object.entries(r.cost || {}).map(([k,v]) => `${v}× ${k}`).join(', ');
    const rc       = RARITY_COL[rarity] || '#9d9d9d';
    const rco      = RARITY_COL[r.output] || '#9d9d9d';
    return `<tr style="opacity:${locked ? '.4' : '1'}">
      <td style="color:${rc};font-family:'Cinzel',serif;font-size:.75rem;padding:5px 8px">${rarity}</td>
      <td style="color:#fff;padding:5px 4px">→</td>
      <td style="color:${rco};font-family:'Cinzel',serif;font-size:.75rem;padding:5px 8px">${r.output}</td>
      <td style="color:var(--text3);font-size:.72rem;padding:5px 8px">${esc(costStr)}</td>
      ${locked ? '<td style="color:var(--accent2);font-size:.68rem;padding:5px 4px">🔒</td>' : '<td></td>'}
    </tr>`;
  }).join('');

  return `
    <div class="pr-form-card">
      <div class="pr-form-title">⬆ Upgrade</div>
      <div class="pr-hint">Povýší item o jeden rarity tier.</div>
      ${table ? `<table style="width:100%;margin-bottom:14px;border-collapse:collapse">${table}</table>` : ''}
      <div class="pr-form-row"><label>Item k upgradu</label>${_itemGridHtml(items, 'prof-upgr-item')}</div>
      <button class="btn btn-gold btn-full" style="margin-top:10px" onclick="doUpgrade()">⬆ Upgrade</button>
    </div>`;
}

async function doUpgrade() {
  const itemId = _profSelectedItem;
  if (!itemId) { toast('Vyber item.', 'e'); return; }
  try {
    const res = await api('POST', '/professions/upgrade', { inventory_item_id: itemId });
    toast(res.message || 'Upgrade dokončen!', 's');
    await _reloadAfterAction();
  } catch(e) {
    toast(e.message, 'e');
  }
}

// ── PO AKCI: reload inventáře + profese ─────────────────────────────────────

async function _reloadAfterAction() {
  // reload inventáře
  if (typeof loadInventory === 'function') await loadInventory();
  // reload profese dat
  try {
    _profDataV3 = await api('GET', '/professions/');
    if (_profDataV3.has_profession) _profRecipes = await api('GET', '/professions/recipes');
    // pouze pravý panel (sidebar se nemění)
    if (_profDataV3?.current) _fillMainPanel(_profDataV3.current);
  } catch(_) {}
  // updateUI
  if (typeof updateUI === 'function' && typeof char !== 'undefined') updateUI(char);
}
