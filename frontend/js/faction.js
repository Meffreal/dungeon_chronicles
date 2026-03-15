// ── FRAKCE (Renown systém) ─────────────────────────────────────────────────

// Lokální data o frakcích (emblem, barva) — synchronizováno se serverem
const FACTION_META = {
  rad_popele:          { emblem: '🔥', color: '#c0392b', dim: 'rgba(192,57,43,0.15)',   name: 'Řád Popele' },
  pakt_stinu:          { emblem: '🌑', color: '#6c3483', dim: 'rgba(108,52,131,0.15)',  name: 'Pakt Stínu' },
  kongregace_prazdna:  { emblem: '🌀', color: '#1a6b8a', dim: 'rgba(26,107,138,0.15)', name: 'Kongregace Prázdna' },
};

let factionData = null;   // cache posledního /faction/my
let allFactions = null;   // cache /faction/info

// ── Načtení stránky frakce ─────────────────────────────────────────────────
async function loadFaction() {
  const wrap = document.getElementById('faction-content');
  if (!wrap) return;

  // Postava ještě neexistuje
  if (!char) {
    wrap.innerHTML = '<div style="color:var(--text2);font-style:italic;text-align:center;padding:40px">Nejdřív si vytvoř postavu.</div>';
    return;
  }

  wrap.innerHTML = '<div style="color:var(--text2);font-style:italic;text-align:center;padding:40px">Načítám...</div>';

  try {
    const [my, info] = await Promise.all([
      api('GET', '/faction/my'),
      allFactions ? null : api('GET', '/faction/info'),
    ]);
    if (info) allFactions = info.factions;

    factionData = my;

    if (!my.faction) {
      renderFactionPicker(wrap);
    } else {
      renderFactionPage(wrap, my);
    }
  } catch(e) {
    wrap.innerHTML = `<div style="color:var(--accent2);text-align:center;padding:40px">${esc(e.message)}</div>`;
  }
}

// ── Picker — hráč nemá frakci ──────────────────────────────────────────────
function renderFactionPicker(wrap) {
  const factions = allFactions || Object.values(FACTION_META).map(m => ({ ...m }));
  const cards = (allFactions || []).map(f => {
    const meta = FACTION_META[f.id] || {};
    return `
      <div class="faction-card" id="fp-card-${f.id}"
           style="--fcard-col:${meta.color};--fcard-bg:${meta.dim};border-color:var(--border)"
           onclick="pickFactionInPage('${f.id}','${esc(f.name)}','${meta.color}','${meta.dim}')">
        <div class="faction-emblem">${meta.emblem || '⚔'}</div>
        <div class="faction-card-name" style="color:${meta.color}">${esc(f.name)}</div>
        <div class="faction-card-tagline">${esc(f.tagline)}</div>
      </div>`;
  }).join('');

  wrap.innerHTML = `
    <div class="page-hdr">⚜ Frakce</div>
    <div style="text-align:center;padding:20px 0 14px">
      <div style="font-family:'Cinzel',serif;font-size:0.85rem;color:var(--text2);margin-bottom:6px">Nezvolil jsi frakci</div>
      <div style="font-size:0.78rem;color:var(--text3);font-style:italic">Zvol svou frakci a začni sbírat reputaci</div>
    </div>
    <div class="faction-grid">${cards || '<div style="color:var(--text3)">Načítání frakcí...</div>'}</div>
    <div id="fp-detail" style="display:none"></div>
    <button id="fp-confirm-btn" class="btn btn-gold btn-full" style="display:none" onclick="confirmChooseFaction()">⚜ Vstoupit do frakce</button>`;
}

let _selectedFaction = null;
function pickFactionInPage(id, name, color, dim) {
  _selectedFaction = id;
  document.querySelectorAll('.faction-card').forEach(c => {
    c.style.borderColor = 'var(--border)';
    c.style.background  = 'var(--panel)';
  });
  const card = document.getElementById(`fp-card-${id}`);
  if (card) { card.style.borderColor = color; card.style.background = dim; }

  // Ukaž detail + confirm btn
  const f = allFactions?.find(f => f.id === id);
  const detail = document.getElementById('fp-detail');
  if (detail && f) {
    detail.style.display = 'block';
    detail.innerHTML = `
      <div style="background:var(--panel);border:1px solid ${color};border-radius:5px;padding:14px;margin-bottom:12px">
        <div style="font-family:'Cinzel',serif;font-size:0.72rem;color:${color};margin-bottom:6px;letter-spacing:1px">${esc(f.lore)}</div>
        <div style="font-size:0.82rem;color:var(--text2);line-height:1.6">${esc(f.description)}</div>
      </div>`;
  }
  const btn = document.getElementById('fp-confirm-btn');
  if (btn) btn.style.display = 'flex';
}

async function confirmChooseFaction() {
  if (!_selectedFaction) return;
  const btn = document.getElementById('fp-confirm-btn');
  if (btn) btn.disabled = true;
  try {
    const d = await api('POST', '/faction/choose', { faction: _selectedFaction, confirm_reset: false });
    factionData = d.faction;
    updateUI(d.character);
    toast(`⚜ Přidal ses k frakci '${FACTION_META[_selectedFaction]?.name}'!`, 's', 4000);
    addAct(`⚜ Přidal ses k frakci: ${FACTION_META[_selectedFaction]?.name}`);
    loadFaction();
  } catch(e) {
    toast(e.message, 'e');
    if (btn) btn.disabled = false;
  }
}

// ── Hlavní stránka frakce ──────────────────────────────────────────────────
function renderFactionPage(wrap, data) {
  const meta    = FACTION_META[data.faction] || {};
  const fi      = data.faction_info || {};
  const current = data.current_tier || {};
  const nxt     = data.next_tier;
  const _prog = Number(data.progress_to_next) || 0;
  const _need = Number(data.needed_for_next)  || 1;   // ochrana proti dělení nulou
  const pct   = nxt ? Math.min(100, Math.max(0, Math.round((_prog / _need) * 100))) : 100;

  const tiersHtml = (data.tiers || []).map(t => {
    if (t.tier === 1) {
      return `<div class="renown-tier unlocked claimed">
        <div class="rt-badge claimed">Startovní</div>
        <div class="rt-num">Tier ${t.tier}</div>
        <div class="rt-name">${esc(t.name)}</div>
        <div class="rt-rep">0 rep</div>
        <div class="rt-reward" style="color:var(--text3);font-style:italic">—</div>
      </div>`;
    }
    const status   = t.claimed ? 'claimed' : t.claimable ? 'claimable' : t.unlocked ? 'unlocked' : 'locked';
    const badgeTxt = t.claimed ? '✓ Sebráno' : t.claimable ? '! K sebrání' : t.unlocked ? 'Odemčeno' : `🔒 ${t.min_rep} rep`;
    const reward   = t.reward || {};
    const claimBtn = t.claimable
      ? `<button class="btn-claim" onclick="claimFactionReward(${t.tier})">🎁 Sebrat odměnu</button>`
      : '';
    return `
      <div class="renown-tier ${status}" style="--fcolor:${meta.color}">
        <div class="rt-badge ${status}">${badgeTxt}</div>
        <div class="rt-num">Tier ${t.tier}</div>
        <div class="rt-name">${esc(t.name)}</div>
        <div class="rt-rep">${t.min_rep} reputace</div>
        <div class="rt-reward">
          <span class="rt-reward-icon">${reward.icon || '🎁'}</span>${esc(reward.label || '—')}
        </div>
        ${claimBtn}
      </div>`;
  }).join('');

  wrap.innerHTML = `
    <!-- Banner frakce -->
    <div class="faction-banner" style="--fcolor:${meta.color};--fdim:${meta.dim}">
      <div class="faction-banner-header">
        <div class="faction-banner-emblem">${meta.emblem || '⚜'}</div>
        <div class="faction-banner-info">
          <div class="faction-banner-name">${esc(fi.name || meta.name || data.faction)}</div>
          <div class="faction-banner-tagline">${esc(fi.tagline || '')}</div>
        </div>
        <button class="btn btn-sm" style="margin-left:auto;opacity:.75"
                onclick="showChangeFactionModal()">Změnit frakci</button>
      </div>

      <!-- Rep bar -->
      <div class="faction-rep-bar-wrap">
        <div class="faction-rep-label">
          <span>${esc(current.name || '')} · ${data.reputation} rep</span>
          <span>${nxt ? `${esc(nxt.name)} za ${data.needed_for_next - data.progress_to_next} rep` : 'MAX'}</span>
        </div>
        <div class="faction-rep-track">
          <div class="faction-rep-fill" style="width:${pct}%;background:${meta.color};box-shadow:0 0 8px ${meta.color}66"></div>
        </div>
        <div class="faction-rep-total">Celková reputace: ${data.reputation}</div>
      </div>
    </div>

    <!-- Lore box -->
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:5px;padding:12px 14px;margin-bottom:16px;font-size:0.82rem;color:var(--text2);line-height:1.6">
      <span style="font-family:'Cinzel',serif;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:${meta.color}">Lore · </span>
      ${esc(fi.lore || '')}
      <div style="margin-top:6px;color:var(--text3);font-style:italic">${esc(fi.description || '')}</div>
    </div>

    <!-- Renown tiery -->
    <div style="font-family:'Cinzel',serif;font-size:0.65rem;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:10px">Renown odměny</div>
    <div class="renown-grid">${tiersHtml}</div>

    <!-- Rep zdroje -->
    <div style="background:var(--panel);border:1px solid var(--border);border-radius:5px;padding:12px 14px;margin-bottom:14px">
      <div style="font-family:'Cinzel',serif;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px">Zdroje reputace</div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;font-size:0.78rem;color:var(--text2)">
        <div>⚔ Quest (snadný): +5 rep</div>
        <div>⚔ Quest (normální): +10 rep</div>
        <div>⚔ Quest (těžký): +15 rep</div>
        <div style="color:var(--text3);font-style:italic">🏟 Aréna: brzy</div>
        <div style="color:var(--text3);font-style:italic">🗺 Dungeony: brzy</div>
      </div>
    </div>`;
}

// ── Claim odměny ───────────────────────────────────────────────────────────
async function claimFactionReward(tierId) {
  try {
    const d = await api('POST', `/faction/claim/${tierId}`);
    factionData = d.faction;
    updateUI(d.character);
    toast(`🎁 ${d.reward_msg}`, 's', 5000);
    addAct(`⚜ Frakční odměna: ${d.reward_msg}`);
    // Překresli stránku
    const wrap = document.getElementById('faction-content');
    if (wrap) renderFactionPage(wrap, d.faction);
    // Pokud je ve vybavení, překresli i to (nové buffy)
    if (document.getElementById('page-equipment')?.classList.contains('active')) renderEquip();
  } catch(e) { toast(e.message, 'e'); }
}

// ── Změna frakce ───────────────────────────────────────────────────────────
function showChangeFactionModal() {
  if (!char?.faction) return;
  const meta = FACTION_META[char.faction] || {};
  const cards = Object.entries(FACTION_META)
    .filter(([id]) => id !== char.faction)
    .map(([id, m]) => {
      const f = allFactions?.find(f => f.id === id) || {};
      return `
        <div class="faction-card" id="fc-card-${id}"
             onclick="pickChangeFaction('${id}','${m.color}','${m.dim}')"
             style="border-color:var(--border)">
          <div class="faction-emblem">${m.emblem}</div>
          <div class="faction-card-name" style="color:${m.color}">${m.name}</div>
          <div class="faction-card-tagline">${esc(f.tagline || '')}</div>
        </div>`;
    }).join('');

  document.getElementById('modal-faction-change-body').innerHTML = `
    <div class="modal-title">⚜ Změnit frakci</div>
    <div class="faction-change-warning">
      ⚠ Změnou frakce nenávratně ztratíš veškerý progress s frakcí
      <strong>${esc(meta.name)}</strong> (${factionData?.reputation || 0} reputace).
      Všechny sebrané odměny si ponecháš, ale reputaci ztratíš.
    </div>
    <div class="faction-section-lbl">Zvol novou frakci</div>
    <div class="faction-grid">${cards}</div>
    <div id="fc-warn" style="display:none" class="faction-change-warning">
      Jsi si <strong>jistý</strong>? Tato akce je nevratná.
    </div>
    <button id="fc-confirm-btn" class="btn btn-full" style="display:none" onclick="confirmChangeFaction()">⚜ Potvrdit změnu frakce</button>
    <button class="btn btn-sm" style="opacity:.6;margin-top:8px;width:100%;justify-content:center" onclick="closeModal('modal-faction-change')">Zrušit</button>`;

  _changeFactionTarget = null;
  openModal('modal-faction-change');
}

let _changeFactionTarget = null;
function pickChangeFaction(id, color, dim) {
  _changeFactionTarget = id;
  document.querySelectorAll('#modal-faction-change-body .faction-card').forEach(c => {
    c.style.borderColor = 'var(--border)';
    c.style.background  = 'var(--panel)';
  });
  const card = document.getElementById(`fc-card-${id}`);
  if (card) { card.style.borderColor = color; card.style.background = dim; }
  document.getElementById('fc-warn').style.display = 'block';
  document.getElementById('fc-confirm-btn').style.display = 'flex';
}

async function confirmChangeFaction() {
  if (!_changeFactionTarget) return;
  const btn = document.getElementById('fc-confirm-btn');
  if (btn) btn.disabled = true;
  try {
    const d = await api('POST', '/faction/choose', { faction: _changeFactionTarget, confirm_reset: true });
    factionData = d.faction;
    updateUI(d.character);
    toast(`⚜ Frakce změněna na '${FACTION_META[_changeFactionTarget]?.name}'!`, 's', 4000);
    addAct(`⚜ Změna frakce: ${FACTION_META[_changeFactionTarget]?.name}`);
    closeModal('modal-faction-change');
    loadFaction();
  } catch(e) {
    toast(e.message, 'e');
    if (btn) btn.disabled = false;
  }
}

// ── Mini faction badge pro vybavení ───────────────────────────────────────
function getFactionBadgeHtml(factionId, reputation) {
  if (!factionId) return '<div class="equip-faction"><div class="faction-chip-no">Bez frakce</div></div>';
  const meta  = FACTION_META[factionId] || {};
  const tier  = getFactionTierName(reputation || 0);
  return `
    <div class="equip-faction" style="--fcolor:${meta.color};--fdim:${meta.dim}">
      <div class="equip-faction-name">${meta.emblem || ''} ${meta.name || factionId}</div>
      <div class="equip-faction-rep">${tier} · ${reputation || 0} rep</div>
    </div>`;
}

function getFactionTierName(rep) {
  const tiers = [[0,'Neznámý'],[100,'Poznaný'],[300,'Důvěrník'],[600,'Spojenec'],[1000,'Šampión'],[1500,'Legenda']];
  let name = tiers[0][1];
  for (const [min, nm] of tiers) { if (rep >= min) name = nm; else break; }
  return name;
}

// ── Faction chip pro přehled ───────────────────────────────────────────────
function getFactionChipHtml(factionId, reputation) {
  if (!factionId) return '<span class="faction-chip-no">Bez frakce</span>';
  const meta = FACTION_META[factionId] || {};
  const tier = getFactionTierName(reputation || 0);
  return `<span class="faction-chip" style="--fcolor:${meta.color};--fdim:${meta.dim}">${meta.emblem || ''} ${meta.name || factionId} · ${tier}</span>`;
}

// ── Faction výběr v modalu tvorby postavy ─────────────────────────────────
let selFaction = null;

function renderFactionGrid() {
  // Deleguj na character.js funkci která má vždy zaručený přístup k DOM
  if (typeof _renderFactionModalGrid === 'function') {
    _renderFactionModalGrid();
    return;
  }
  // Fallback (přímo zde)
  const wrap = document.getElementById('faction-grid-modal');
  if (!wrap) return;
  wrap.innerHTML = Object.entries(FACTION_META).map(([id, m]) => {
    const f = allFactions?.find(f => f.id === id) || {};
    return `
      <div class="faction-card" id="fm-${id}"
           onclick="_pickFactionModal('${id}','${m.color}','${m.dim}')"
           style="border-color:var(--border)">
        <div class="faction-emblem">${m.emblem}</div>
        <div class="faction-card-name" style="color:${m.color}">${m.name}</div>
        <div class="faction-card-tagline" style="font-size:.62rem;color:var(--text3);font-style:italic">${esc(f.tagline || '')}</div>
      </div>`;
  }).join('');
  if (selFaction) _pickFactionModal(selFaction, FACTION_META[selFaction]?.color, FACTION_META[selFaction]?.dim);
}

function pickModalFaction(id, color, dim) {
  selFaction = id;
  document.querySelectorAll('#faction-grid-modal .faction-card').forEach(c => {
    c.style.borderColor = 'var(--border)';
    c.style.background  = 'var(--panel)';
  });
  const card = document.getElementById(`fm-${id}`);
  if (card) { card.style.borderColor = color; card.style.background = dim; }
}
