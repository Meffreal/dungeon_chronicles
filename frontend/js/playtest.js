// frontend/js/playtest.js
// Playtest roguelite dungeon systém — izolovaný od starého dungeon.js

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
let _ptRun        = null;   // aktuální PlaytestRun nebo null
let _ptDungeons   = [];     // seznam dungeonů
let _ptPendingRelics = [];  // čekající relic nabídka
let _ptActiveNode = null;   // ID uzlu čekajícího na akci

// ── Init ──────────────────────────────────────────────────────────────────────
async function initPlaytest() {
  try {
    await _ptRefresh();
  } catch (e) {
    document.getElementById('pt-content').innerHTML =
      `<p style="color:var(--clr-muted)">Nepodařilo se načíst Playtest.</p>`;
  }
}

async function _ptRefresh() {
  const data = await api('GET', '/playtest/dungeon/list');
  _ptDungeons = data.dungeons;
  _ptRun      = data.active_run;
  _ptRender();
}

// ── Render router ─────────────────────────────────────────────────────────────
function _ptRender() {
  const el = document.getElementById('pt-content');
  if (!el) return;

  if (!_ptRun) {
    el.innerHTML = _ptRenderList();
    return;
  }
  if (_ptRun.status === 'completed' || _ptRun.status === 'failed') {
    el.innerHTML = _ptRenderCollect();
    return;
  }
  // Aktivní run
  el.innerHTML = _ptRenderActiveRun();
  _ptBindMapClicks();
}

// ── List view ─────────────────────────────────────────────────────────────────
function _ptRenderList() {
  const cards = _ptDungeons.map(d => {
    const locked     = d.locked;
    const onCooldown = d.on_cooldown;
    const cdText     = onCooldown ? _ptCooldownText(d.cooldown_until) : '';

    let btnHtml = '';
    if (locked)
      btnHtml = `<div class="pt-cooldown-timer">Vyžaduje level ${d.min_level}</div>`;
    else if (onCooldown)
      btnHtml = `<div class="pt-cooldown-timer">${cdText}</div>`;
    else
      btnHtml = `<button class="pt-enter-btn" onclick="ptEnter('${d.key}')">Vstoupit</button>`;

    return `
      <div class="pt-dungeon-card ${locked ? 'locked' : ''} ${onCooldown ? 'on-cooldown' : ''}">
        <h3>${d.name}</h3>
        <div class="pt-card-meta">Min. úroveň ${d.min_level} · Cooldown ${d.cooldown_hours}h</div>
        ${btnHtml}
      </div>`;
  }).join('');

  return `<div class="pt-dungeon-list">${cards}</div>`;
}

// ── Active run view ───────────────────────────────────────────────────────────
function _ptRenderActiveRun() {
  const run     = _ptRun;
  const hpPct   = Math.max(0, Math.round((run.hp_current / run.hp_max) * 100));
  const critical = hpPct < 30;

  const relicChips = (run.relics || []).map(r =>
    `<div class="pt-relic-chip ${r.consumed ? 'consumed' : ''}" title="${r.desc || ''}">${r.name}</div>`
  ).join('');

  const sidebar = `
    <div class="pt-sidebar">
      <div class="pt-hp-bar-wrap">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:.85rem">
          <span>HP</span><span>${run.hp_current} / ${run.hp_max}</span>
        </div>
        <div class="pt-hp-bar-bg">
          <div class="pt-hp-bar-fill ${critical ? 'critical' : ''}" style="width:${hpPct}%"></div>
        </div>
        ${critical ? '<div style="color:#ef4444;font-size:.75rem;margin-top:4px">⚠️ Kritické HP!</div>' : ''}
      </div>
      <div style="font-size:.8rem;color:var(--clr-muted);margin-bottom:4px">Relics:</div>
      <div class="pt-relics-list">${relicChips || '<span style="color:var(--clr-muted);font-size:.8rem">Žádné</span>'}</div>
      <div class="pt-rewards-mini">
        <div>XP: +${run.reward_xp}</div>
        <div>Gold: ${run.run_gold}g</div>
      </div>
      <button onclick="ptAbandon(${run.id})" style="width:100%;margin-top:16px;padding:8px;background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3);border-radius:8px;cursor:pointer;font-size:.85rem">
        Opustit run
      </button>
    </div>`;

  const mapSvg = _ptRenderMapSvg(run.map_data);

  return `
    <div class="pt-run-layout">
      ${sidebar}
      <div class="pt-map-wrap">
        <div style="font-size:.85rem;color:var(--clr-muted);margin-bottom:12px">
          ${PLAYTEST_DUNGEONS_NAMES[run.dungeon_key] || run.dungeon_key}
          — klikni na dostupný uzel
        </div>
        ${mapSvg}
      </div>
    </div>`;
}

const PLAYTEST_DUNGEONS_NAMES = {
  pt_tomb:    'Tomb of Forgotten',
  pt_fiery:   'Fiery Depths',
  pt_citadel: 'Citadel of Chaos',
};

// ── SVG mapa ──────────────────────────────────────────────────────────────────
const NODE_ICONS = {
  start:  '🏁', combat: '⚔️', elite: '💀', rest: '🛖',
  event:  '❓', shop:   '💰', boss:  '👑',
};

function _ptRenderMapSvg(mapData) {
  if (!mapData || !mapData.nodes) return '<p>Mapa nenalezena.</p>';

  // Normalizuj layout souřadnice na SVG prostor (0-500 x 0-280)
  const layout = mapData.layout;
  const xs = Object.values(layout).map(p => p[0]);
  const ys = Object.values(layout).map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const W = 500, H = 280, PAD = 40;

  const toSvg = (x, y) => {
    const sx = maxX === minX ? W / 2 : PAD + ((x - minX) / (maxX - minX)) * (W - PAD * 2);
    const sy = maxY === minY ? H / 2 : PAD + ((y - minY) / (maxY - minY)) * (H - PAD * 2);
    return [sx, sy];
  };

  // Edges
  let edgesSvg = '';
  for (const [src, dst] of (mapData.edges || [])) {
    if (!layout[src] || !layout[dst]) continue;
    const [x1, y1] = toSvg(...layout[src]);
    const [x2, y2] = toSvg(...layout[dst]);
    edgesSvg += `<line class="pt-edge" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
  }

  // Nodes
  let nodesSvg = '';
  for (const [nid, node] of Object.entries(mapData.nodes)) {
    if (!layout[nid]) continue;
    const [cx, cy] = toSvg(...layout[nid]);
    const status   = node.status;
    const icon     = NODE_ICONS[node.type] || '?';
    nodesSvg += `
      <g class="pt-node ${status}" data-node-id="${nid}" data-node-type="${node.type}">
        <circle cx="${cx}" cy="${cy}" r="22" fill="var(--clr-surface)" stroke="rgba(255,255,255,.15)" stroke-width="1.5"/>
        <text x="${cx}" y="${cy - 4}" font-size="14">${icon}</text>
        <text x="${cx}" y="${cy + 12}" font-size="9" fill="rgba(255,255,255,.6)">${node.type}</text>
      </g>`;
  }

  return `<svg class="pt-map-svg" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
    ${edgesSvg}${nodesSvg}
  </svg>`;
}

function _ptBindMapClicks() {
  document.querySelectorAll('.pt-node.available').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const nodeId   = el.dataset.nodeId;
      const nodeType = el.dataset.nodeType;
      _ptShowNodeModal(nodeId, nodeType);
    });
  });
}

// ── Collect view ──────────────────────────────────────────────────────────────
function _ptRenderCollect() {
  const run   = _ptRun;
  const won   = run.status === 'completed';
  const title = won ? '🏆 Dungeon dokončen!' : '💀 Run selhal';
  const color = won ? '#a78bfa' : '#ef4444';

  return `
    <div class="pt-collect-summary">
      <h3 style="color:${color}">${title}</h3>
      <div class="pt-collect-rewards">
        <div class="pt-collect-reward-item">
          <span>+${run.reward_xp}</span><span>XP</span>
        </div>
        ${won ? `<div class="pt-collect-reward-item"><span>+${run.run_gold}g</span><span>Gold</span></div>` : ''}
      </div>
      <button class="pt-collect-btn" onclick="ptCollect(${run.id})">Vyzvednout odměny</button>
    </div>`;
}

// ── Node modaly ───────────────────────────────────────────────────────────────
function _ptShowNodeModal(nodeId, nodeType) {
  _ptActiveNode = nodeId;
  const mapData = _ptRun.map_data;
  const node    = mapData.nodes[nodeId];
  if (!node) return;

  let body = '';
  let title = '';

  if (nodeType === 'combat' || nodeType === 'elite' || nodeType === 'boss') {
    title = nodeType === 'boss' ? '👑 Boss' : nodeType === 'elite' ? '💀 Elite' : '⚔️ Combat';
    body = `
      <p>Nepřítel: <strong>${node.enemy_name}</strong></p>
      <p style="color:var(--clr-muted);font-size:.85rem">Síla: ${Math.round(node.enemy_mult * 100)}%</p>
      <p style="color:var(--clr-muted);font-size:.85rem">Odměna: +${node.reward_xp} XP · +${node.reward_gold}g</p>
      <button onclick="ptChooseNode('${nodeId}')" class="pt-enter-btn" style="margin-top:12px">
        Vstoupit do boje
      </button>`;
  } else if (nodeType === 'rest') {
    const heal = Math.floor(_ptRun.hp_max * 0.25);
    title = '🛖 Odpočinek';
    body = `
      <p>Obnov <strong>${heal} HP</strong>.</p>
      <button onclick="ptChooseNode('${nodeId}')" class="pt-enter-btn" style="margin-top:12px;background:#22c55e">
        Odpočinout (+${heal} HP)
      </button>`;
  } else if (nodeType === 'event') {
    title = '❓ Událost';
    body = `<p style="color:var(--clr-muted)">Načítám událost...</p>`;
  } else if (nodeType === 'shop') {
    title = '💰 Obchod';
    body = `
      <p style="color:var(--clr-muted)">Run gold: <strong>${_ptRun.run_gold}g</strong></p>
      <div class="pt-shop-items">
        ${_ptShopItems()}
      </div>
      <button onclick="ptSkipShop('${nodeId}')" style="width:100%;margin-top:12px;padding:8px;background:transparent;color:var(--clr-muted);border:1px solid rgba(255,255,255,.1);border-radius:8px;cursor:pointer">
        Přejít bez nákupu
      </button>`;
  }

  document.getElementById('pt-modal-title').textContent = title;
  document.getElementById('pt-modal-body').innerHTML    = body;
  openModal('modal-playtest-node');

  if (nodeType === 'event') {
    ptChooseNodeEvent(nodeId);
  }
}

function _ptShopItems() {
  const items = [
    { id: 'heal',          label: 'Léčení (40% HP)',        cost: 50  },
    { id: 'atk_boost',     label: 'Útočný boost (+10% ATK)', cost: 80  },
    { id: 'relic_refresh', label: 'Nový relic výběr',        cost: 120 },
  ];
  return items.map(item => {
    const canAfford = _ptRun.run_gold >= item.cost;
    return `
      <div class="pt-shop-item">
        <span>${item.label}</span>
        <button class="pt-shop-buy-btn" ${canAfford ? '' : 'disabled'}
          onclick="ptShopBuy('${item.id}')">
          ${item.cost}g
        </button>
      </div>`;
  }).join('');
}

// ── Relic picker modal ────────────────────────────────────────────────────────
function _ptShowRelicModal(relics) {
  _ptPendingRelics = relics;
  const cards = relics.map(r => `
    <div class="pt-relic-card" onclick="ptChooseRelic('${r.id}')">
      <h4>${r.name}</h4>
      <p>${r.desc}</p>
    </div>`).join('');

  document.getElementById('pt-relic-cards').innerHTML = cards;
  openModal('modal-playtest-relic');
}

// ── API akce ──────────────────────────────────────────────────────────────────
async function ptEnter(dungeonKey) {
  try {
    const data  = await api('POST', '/playtest/dungeon/enter', { dungeon_key: dungeonKey });
    _ptRun      = data.run;
    _ptRender();
    closeModal('modal-playtest-node');
  } catch (e) {
    toast(e.message || 'Chyba při vstupu do dungeonu', 'e');
  }
}

async function ptChooseNode(nodeId) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId });
    _ptRun = data.run;

    if (data.action === 'combat_win' || data.action === 'boss_win') {
      if (data.battle_log && data.battle_log.length) {
        await showCombatReplay(data.battle_log, true, () => {
          if (data.pending_relics && data.pending_relics.length) {
            _ptShowRelicModal(data.pending_relics);
          } else {
            _ptRender();
          }
        });
      } else if (data.pending_relics && data.pending_relics.length) {
        _ptShowRelicModal(data.pending_relics);
      } else {
        _ptRender();
      }
      if (data.xp) toast(`+${data.xp} XP · +${data.gold}g`, 's');
    } else if (data.action === 'combat_loss') {
      if (data.battle_log && data.battle_log.length) {
        await showCombatReplay(data.battle_log, false, () => _ptRender());
      } else {
        _ptRender();
      }
      toast('Poražen! Run selhal.', 'e');
    } else if (data.action === 'rest') {
      toast(`Odpočinek: +${data.hp_restored} HP`, 's');
      _ptRender();
    } else if (data.action === 'event') {
      _ptShowEventInModal(data.event_data, nodeId);
    } else if (data.action === 'shop') {
      _ptShowNodeModal(nodeId, 'shop');
    } else {
      _ptRender();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
    _ptRender();
  }
}

async function ptChooseNodeEvent(nodeId) {
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId });
    if (data.action === 'event') {
      _ptShowEventInModal(data.event_data, nodeId);
    }
  } catch (e) {
    toast(e.message || 'Chyba při načítání eventu', 'e');
  }
}

function _ptShowEventInModal(eventData, nodeId) {
  document.getElementById('pt-modal-title').textContent = '❓ Událost';
  const choiceBtns = eventData.choices.map(c => `
    <button onclick="ptChooseEvent(${c.index})" style="width:100%;margin-bottom:8px;padding:12px;background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);border-radius:8px;cursor:pointer;text-align:left">
      <strong>${c.label}</strong>
      <div style="font-size:.8rem;color:var(--clr-muted);margin-top:4px">${c.hint}</div>
    </button>`).join('');
  document.getElementById('pt-modal-body').innerHTML =
    `<p style="margin-bottom:16px">${eventData.text}</p>${choiceBtns}`;
  if (!document.getElementById('modal-playtest-node').classList.contains('open')) {
    openModal('modal-playtest-node');
  }
}

async function ptChooseEvent(choiceIndex) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-event',
      { run_id: _ptRun.id, choice_index: choiceIndex });
    _ptRun = data.run;
    toast(data.outcome_text || 'Událost vyřešena', 's');
    if (data.hp_delta < 0) toast(`HP: ${data.hp_delta}`, 'e');
    if (data.gold_delta > 0) toast(`+${data.gold_delta}g`, 's');
    if (data.pending_relics && data.pending_relics.length) {
      _ptShowRelicModal(data.pending_relics);
    } else {
      _ptRender();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptChooseRelic(relicId) {
  closeModal('modal-playtest-relic');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-relic',
      { run_id: _ptRun.id, relic_id: relicId });
    _ptRun = data.run;
    if (data.description) toast(data.description, 's');
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptShopBuy(itemId) {
  try {
    const data = await api('POST', '/playtest/dungeon/shop-buy',
      { run_id: _ptRun.id, item_id: itemId });
    _ptRun = data.run;
    if (data.hp_restored) toast(`Léčení: +${data.hp_restored} HP`, 's');
    if (data.pending_relics && data.pending_relics.length) {
      closeModal('modal-playtest-node');
      _ptShowRelicModal(data.pending_relics);
    } else {
      const shopItemsEl = document.getElementById('pt-modal-body').querySelector('.pt-shop-items');
      if (shopItemsEl) shopItemsEl.innerHTML = _ptShopItems();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptSkipShop(nodeId) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId, skip_shop: true });
    _ptRun = data.run;
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptCollect(runId) {
  try {
    const data = await api('POST', '/playtest/dungeon/collect', { run_id: runId });
    _ptRun = null;
    if (data.xp_gained) toast(`+${data.xp_gained} XP`, 's');
    if (data.gold_gained) toast(`+${data.gold_gained}g`, 's');
    if (data.leveled_up && data.leveled_up.length) {
      data.leveled_up.forEach(lvl => toast(`Level up! → ${lvl}`, 's'));
    }
    if (data.character) {
      char = data.character;
      updateUI(char);
    }
    await _ptRefresh();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptAbandon(runId) {
  if (!await _ptConfirm('Opustit run? Získáš pouze 50% nahromaděného XP.')) return;
  try {
    const data = await api('POST', '/playtest/dungeon/abandon', { run_id: runId });
    _ptRun = data.run;
    toast('Run opuštěn.', 'i');
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

// ── Confirm helper ────────────────────────────────────────────────────────────
function _ptConfirm(message) {
  return new Promise(resolve => {
    document.getElementById('pt-confirm-text').textContent = message;
    document.getElementById('pt-confirm-ok').onclick = () => {
      closeModal('modal-playtest-confirm'); resolve(true);
    };
    document.getElementById('pt-confirm-cancel').onclick = () => {
      closeModal('modal-playtest-confirm'); resolve(false);
    };
    openModal('modal-playtest-confirm');
  });
}

// ── Cooldown helper ───────────────────────────────────────────────────────────
function _ptCooldownText(isoStr) {
  if (!isoStr) return '';
  const diff = new Date(isoStr) - Date.now();
  if (diff <= 0) return 'Připraven';
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `Cooldown: ${h}h ${m}m`;
}
