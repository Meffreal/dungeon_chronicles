// ── PROFESE ────────────────────────────────────────────────────────────────

const PROF_META = {
  runist: { name: 'Runist',  icon: '✦',  color: '#e8b020', dim: 'rgba(232,176,32,0.10)',  desc: 'Mistr runových inscripcí a dušekovářství. Vyrývá magické runy do vybavení a taví gear v dungeon výhni na nové artefakty. Pasivní: Rezonance run.' },
  oracle: { name: 'Věštec',  icon: '🔮', color: '#20c8d8', dim: 'rgba(32,200,216,0.10)',  desc: 'Předpovídá osudy a tká pouta mezi hráči i duchy. Věští výsledky questů, prodává svitky proroctví a ovládá karmu světa. Pasivní: +2 % XP z questů za každý rank.' },
  broker: { name: 'Makléř', icon: '🎲', color: '#9040e0', dim: 'rgba(144,64,224,0.10)', desc: 'Expert na riziko a stínové kontrakty. Uzavírá sázky, pořádá loterie a provádí tajné agentské operace pod pseudonymem. Pasivní: +5 % zlata z questů za každý rank.' },
};

// FIX: synced with backend models/profession.py RANK_NAMES
const RANK_NAMES = ['Novic', 'Učedník', 'Tovaryš', 'Expert', 'Mistr', 'Velmistr'];

let _profData        = null;   // cached GET /professions/
let _profView        = 'hub';  // 'hub' | profession key
let _profSubTab      = 'info'; // active sub-tab
let _forgeSelectedIds = [];    // IDs inventárních itemů vybraných pro tavení

// ── PRŮVODCE PROFESEMI ───────────────────────────────────────────────────────
const PROF_GUIDE = {
  runist: {
    quick: 'Vyrývej runy do vybavení a tav gear v dungeon výhni. Správné runové kombinace tvoří synergie — a z taveného lomu vznikají nové artefakty.',
    steps: [
      'Runy: jdi do Inventáře a klikni na libovolný item → vyber runu z repertoáru',
      'Opakuj pro druhý slot — kombinace run může tvořit synergii nebo konflikt',
      'Výheň: vyber 2–4 itemy v záložce Výheň, zvol cílový typ a spusť tavení',
    ],
    mechanics: [
      { icon: '✦', label: 'Runové sloty', desc: 'Každý item má 2 sloty. Runu lze nahradit, ale stará se smaže.' },
      { icon: '⚡', label: 'Synergie / Konflikty', desc: 'Určité dvojice run se vzájemně posilují. Jiné kolidují a ruší se.' },
      { icon: '🔥', label: 'Forge', desc: '3 sloty paralelně. Průměrná rarity vstupů ± 1 tier náhodou. 4× epic může dát legendary.' },
      { icon: '★', label: 'Pasivní: Rezonance', desc: 'Aktivní runy rezonují s questovými mechanikami — slabší efekty i mimo přímé interakce.' },
    ],
    xp: ['Za každé úspěšné rytí runy', 'Za aktivaci synergie', 'XP závisí na raritě forge výsledku'],
    warn: '⚠ Vstupní itemy pro tavení jsou zničeny vždy — i při selhání.',
  },
  oracle: {
    quick: 'Věšti výsledky questů, prodávej svitky proroctví a tká pouta osudu. Pasivní bonus +2 % XP z questů za každý rank.',
    steps: [
      'Věštby: vytvoř věštbu, nastav cenu → svitek se objeví na burze',
      'Pouta: vyber dva hráče a typ pouta (spolupráce, prokletí…)',
      'Duchové: přivolej NPC ducha pro slabší pouto bez souhlasu cíle',
    ],
    mechanics: [
      { icon: '📜', label: 'Svitky', desc: 'Max 10 nevyřízených svitků najednou. Kupující vidí téma, ne konkrétní hodnotu.' },
      { icon: '📊', label: 'Přesnost', desc: '≥70 % nebo ≥90 % týdenní přesnost přináší velké XP bonusy každý týden.' },
      { icon: '🌀', label: 'Pouta', desc: '+10 % XP, +12 % ATK, nebo −8 % quest šance cíle. Max 3 hráčská + 2 duchová.' },
      { icon: '☯', label: 'Pasivní: Prozření', desc: '+2 % XP z questů za každý rank (max +10 % na rank 5). Přidáno k základnímu XP.' },
    ],
    xp: ['+10/25/120 XP za věštbu/prodej/správnou předpověď', '+50 XP za hráčské pouto', '+40 XP za každý "oheň" (úspěch cíle)'],
    warn: '⚠ Prokletí zvyšuje karmu. Při 10 bodech nemůžeš tvořit pouta dokud nedokončíš quest Smíření.',
  },
  broker: {
    quick: 'Uzavírej sázky, pořádej loterie a prováděj tajné operace pod pseudonymem. Pasivní bonus +5 % zlata z questů za každý rank.',
    steps: [
      'Sázky: vytvoř sázku vs Stínový dům (ihned) nebo jiný hráč (musí přijmout)',
      'Operace: založ identitu → vyber typ a obtížnost → počkej a seber výsledky',
      'Loterie: nastav vstupné a čas losování — ostatní hráči se přihlásí',
    ],
    mechanics: [
      { icon: '🏠', label: 'Stínový dům', desc: '15% výhoda (edge). Po sérii výher roste podezření a kurzy se zhorší.' },
      { icon: '🎭', label: 'Identita', desc: 'Pseudonym skrývá jméno při operacích. Detekce = odhalení na 72h.' },
      { icon: '📈', label: 'Obtížnost operací', desc: 'Vyšší obtížnost = větší odměna, ale vyšší šance detekce. Rank ji snižuje.' },
      { icon: '🎲', label: 'Pasivní: Riziková prémie', desc: '+5 % zlata z questů za každý rank (max +25 % na rank 5). Přidáno k základnímu zlatu.' },
    ],
    xp: ['+15/48/80 XP za sázku/výhru Shadow/výhru PvP', '+200 XP za organizaci loterie', 'XP za operace dle obtížnosti'],
    warn: 'Max 5 otevřených sázek. Vklad se strhne okamžitě. Detekce kompromituje identitu na 72h.',
  },
};

// ── LOAD ────────────────────────────────────────────────────────────────────
async function loadProfessions() {
  const wrap = document.getElementById('prof-content');
  if (!wrap) return;

  if (!char) {
    wrap.innerHTML = '<div style="color:var(--text2);font-style:italic;text-align:center;padding:40px">Nejdřív si vytvoř postavu.</div>';
    return;
  }

  wrap.innerHTML = '<div style="color:var(--text2);font-style:italic;text-align:center;padding:30px">Načítám profese...</div>';

  try {
    _profData = await api('GET', '/professions/');
    _profView = 'hub';
    renderProfHub(wrap);
  } catch(e) {
    wrap.innerHTML = `<div style="color:var(--accent2);text-align:center;padding:40px">${esc(e.message)}</div>`;
  }
}

// ── HUB VIEW ────────────────────────────────────────────────────────────────
function renderProfHub(wrap) {
  const profs = _profData?.professions || [];

  // Active slots
  const activeProfs = profs.filter(p => p.is_active).sort((a,b) => (a.slot||1) - (b.slot||1));
  const slotsHtml = [0,1].map(i => {
    const p = activeProfs.find(p => (p.slot - 1) === i);
    if (p) {
      // FIX: p.profession_key (not p.key)
      const meta = PROF_META[p.profession_key] || {};
      const rankName = RANK_NAMES[p.rank] || 'Novic';
      // FIX: p.xp_to_next (not p.xp_to_next_rank)
      const xpPct = p.xp_to_next > 0 ? Math.round((p.xp / p.xp_to_next) * 100) : 100;
      return `
        <div class="pr-slot is-active" style="--pcol:${meta.color};--pdim:${meta.dim}" onclick="openProfView('${p.profession_key}')">
          <div class="pr-slot-corner">Slot ${i+1}</div>
          <div class="pr-slot-ico">${meta.icon}</div>
          <div class="pr-slot-info">
            <div class="pr-slot-name">${meta.name}</div>
            <div class="pr-slot-rank">${rankName}</div>
            <div class="pr-xpbar-track"><div class="pr-xpbar-fill" style="width:${xpPct}%;background:${meta.color}"></div></div>
            <div class="pr-slot-xplabel">${p.xp_to_next > 0 ? `${p.xp}/${p.xp_to_next} XP` : 'MAX'}</div>
          </div>
        </div>`;
    } else {
      return `
        <div class="pr-slot is-empty">
          <div class="pr-slot-corner">Slot ${i+1}</div>
          <div class="pr-slot-ico" style="opacity:.25">⊕</div>
          <div class="pr-slot-info">
            <div class="pr-slot-name" style="color:var(--text3)">Volný slot</div>
            <div class="pr-slot-rank" style="color:var(--border2)">Aktivuj profesi níže</div>
          </div>
        </div>`;
    }
  }).join('');

  // Profession cards
  const cardsHtml = Object.entries(PROF_META).map(([key, meta]) => {
    // FIX: p.profession_key (not p.key)
    const p = profs.find(p => p.profession_key === key);
    let badge, xpBar = '', statLine = '';

    if (!p || p.status === 'available') {
      // FIX: backend returns next_learn_cost at top level, not per-profession learn_costs dict
      const cost = _profData?.next_learn_cost;
      badge = `<div class="pr-badge pr-badge-avail">${cost != null ? cost + ' G' : 'Dostupná'}</div>`;
      statLine = `<div class="pr-card-stat pr-stat-avail">Nenaučena</div>`;
    } else if (p.is_active) {
      const rankName = RANK_NAMES[p.rank] || 'Novic';
      // FIX: p.xp_to_next (not p.xp_to_next_rank)
      const xpPct = p.xp_to_next > 0 ? Math.round((p.xp / p.xp_to_next) * 100) : 100;
      badge = `<div class="pr-badge pr-badge-active">⚡ Slot ${p.slot}</div>`;
      xpBar = `<div class="pr-xpbar-track" style="margin-top:8px"><div class="pr-xpbar-fill" style="width:${xpPct}%;background:${meta.color}"></div></div>`;
      statLine = `<div class="pr-card-stat" style="color:${meta.color}">${rankName} · ${p.xp_to_next > 0 ? `${p.xp}/${p.xp_to_next} XP` : 'MAX'}</div>`;
    } else {
      const rankName = RANK_NAMES[p.rank] || 'Novic';
      badge = `<div class="pr-badge pr-badge-learned">✓ Naučena</div>`;
      statLine = `<div class="pr-card-stat pr-stat-dormant">${rankName} · Dormantní</div>`;
    }

    return `
      <div class="pr-card ${p?.is_active ? 'is-active' : (!p || p.status === 'available') ? 'is-available' : 'is-learned'}"
           style="--pcol:${meta.color};--pdim:${meta.dim}"
           onclick="openProfView('${key}')">
        <div class="pr-card-header">
          <div class="pr-card-ico">${meta.icon}</div>
          <div style="flex:1;min-width:0">
            ${badge}
            <div class="pr-card-name">${meta.name}</div>
          </div>
          <div class="pr-card-arrow">›</div>
        </div>
        <div class="pr-card-desc">${meta.desc}</div>
        ${statLine}
        ${xpBar}
      </div>`;
  }).join('');

  // Rune-fall decoration symbols
  const runeSymbols = ['✦','◈','⊕','✧','⊗','✴','◆','⬡'];

  wrap.innerHTML = `
    <div class="pr-hero">
      <div class="pr-hero-runes" aria-hidden="true">
        ${runeSymbols.map((r,i) => `<span style="left:${5+i*12}%;animation-delay:${i*1.4}s;animation-duration:${10+i*1.5}s">${r}</span>`).join('')}
      </div>
      <div class="pr-hero-inner">
        <div class="pr-hero-icon">⚗</div>
        <div class="pr-hero-title">Profese</div>
        <div class="pr-hero-sub">Ovládni umění specializace. Aktivuj až <em>2 profese</em> současně a prohlubuj jejich moc.</div>
      </div>
    </div>

    <div class="pr-section-label">Aktivní sloty</div>
    <div class="pr-slots">${slotsHtml}</div>

    <div class="pr-section-label" style="margin-top:22px">Všechny profese</div>
    <div class="pr-grid">${cardsHtml}</div>
  `;
}

// ── DETAIL VIEW ─────────────────────────────────────────────────────────────
function openProfView(key) {
  _profView   = key;
  _profSubTab = getProfTabs(key)[0]?.id || 'info';
  const wrap  = document.getElementById('prof-content');
  renderProfDetail(wrap, key);
}

function renderProfDetail(wrap, key) {
  const meta  = PROF_META[key] || { name: key, icon: '⚗', color: '#c89010', dim: 'rgba(200,144,32,0.1)', desc: '' };
  const profs = _profData?.professions || [];
  // FIX: p.profession_key (not p.key)
  const p     = profs.find(p => p.profession_key === key);

  // ── Action button ──
  let actionBtn = '';
  if (!p || p.status === 'available') {
    // FIX: backend returns next_learn_cost at top level, not per-profession learn_costs dict
    const cost = _profData?.next_learn_cost ?? '?';
    actionBtn = `<button class="pr-action-btn pr-action-learn" onclick="learnProfession('${key}')">⚗ Naučit se · ${cost} G</button>`;
  } else if (!p.is_active) {
    if (p.slot_locked_until && new Date(p.slot_locked_until) > new Date()) {
      const until = new Date(p.slot_locked_until).toLocaleString('cs', {hour:'2-digit',minute:'2-digit'});
      actionBtn = `<button class="pr-action-btn" disabled>🔒 Cooldown do ${until}</button>`;
    } else {
      // FIX: activateProfession now requires replace_slot — determine which slot to fill
      const slot1 = profs.find(p2 => p2.is_active && p2.slot === 1);
      const slot2 = profs.find(p2 => p2.is_active && p2.slot === 2);
      if (!slot1) {
        actionBtn = `<button class="pr-action-btn pr-action-activate" onclick="activateProfession('${key}', 1)">⚡ Aktivovat do Slotu 1</button>`;
      } else if (!slot2) {
        actionBtn = `<button class="pr-action-btn pr-action-activate" onclick="activateProfession('${key}', 2)">⚡ Aktivovat do Slotu 2</button>`;
      } else {
        // Both slots taken — let player choose which to replace
        const m1 = PROF_META[slot1.profession_key] || {};
        const m2 = PROF_META[slot2.profession_key] || {};
        actionBtn = `
          <div class="pr-slot-pick">
            <div class="pr-slot-pick-lbl" style="color:var(--text2);font-size:0.72rem;margin-bottom:6px">Nahradit slot:</div>
            <button class="pr-action-btn pr-action-activate" style="margin-bottom:5px" onclick="activateProfession('${key}', 1)">Slot 1: ${m1.name||slot1.profession_key}</button>
            <button class="pr-action-btn pr-action-activate" onclick="activateProfession('${key}', 2)">Slot 2: ${m2.name||slot2.profession_key}</button>
          </div>`;
      }
    }
  } else {
    actionBtn = `<div class="pr-active-pill" style="border-color:${meta.color};color:${meta.color}">⚡ Aktivní · Slot ${p.slot}</div>`;
  }

  // ── Rank block ──
  let rankHtml = '';
  if (p) {
    const rank    = p.rank || 0;
    const rankName = RANK_NAMES[rank] || 'Novic';
    const xp      = p.xp || 0;
    // FIX: p.xp_to_next (not p.xp_to_next_rank)
    const xpNext  = p.xp_to_next || 0;
    const xpPct   = xpNext > 0 ? Math.min(100, Math.round(xp / xpNext * 100)) : 100;
    const starsHtml = Array.from({length:5}, (_,i) =>
      `<span class="pr-star" style="color:${i < rank ? meta.color : 'var(--border2)'}">★</span>`
    ).join('');

    rankHtml = `
      <div class="pr-rank-row">
        <div class="pr-rank-badge" style="border-color:${meta.color}44;background:${meta.color}11;color:${meta.color}">${rankName}</div>
        <div class="pr-stars">${starsHtml}</div>
      </div>
      <div class="pr-xp-row">
        <div class="pr-xp-track"><div class="pr-xp-fill" style="width:${xpPct}%;background:${meta.color};box-shadow:0 0 8px ${meta.color}66"></div></div>
        <div class="pr-xp-label">${xpNext > 0 ? `${xp} / ${xpNext} XP` : 'MAX RANK'}</div>
      </div>`;
  } else {
    rankHtml = `<div class="pr-unlearned-note">Profese není naučena. Naučení ti odemkne její obsah.</div>`;
  }

  // ── Sub-tabs ──
  const tabs    = p?.is_active ? getProfTabs(key) : [];
  const tabsHtml = tabs.length ? `
    <div class="pr-tabs">
      ${tabs.map(t => `<button class="pr-tab ${_profSubTab === t.id ? 'active' : ''}"
        onclick="switchProfTab('${key}','${t.id}',this)">${t.label}</button>`).join('')}
    </div>` : '';

  wrap.innerHTML = `
    <button class="pr-back" onclick="backToProfHub()">← Zpět na profese</button>

    <div class="pr-detail-banner" style="--pcol:${meta.color};--pdim:${meta.dim}">
      <div class="pr-detail-glow" style="background:radial-gradient(ellipse at 20% 50%, ${meta.color}18 0%, transparent 70%)"></div>
      <div class="pr-detail-left">
        <div class="pr-detail-ico">${meta.icon}</div>
        <div class="pr-detail-title-block">
          <div class="pr-detail-name">${meta.name}</div>
          <div class="pr-detail-desc">${meta.desc}</div>
          ${rankHtml}
        </div>
      </div>
      <div class="pr-detail-right">${actionBtn}</div>
    </div>

    ${tabsHtml}

    <div id="prof-sub-content" class="pr-sub-content">
      ${!p?.is_active
        ? `<div class="pr-locked-notice">${(!p || p.status === 'available') ? '⚗ Naučte se tuto profesi pro přístup k jejím funkcím.' : '⚡ Aktivuj profesi pro přístup k jejím funkcím.'}</div>`
        : ''}
    </div>
  `;

  if (p?.is_active && tabs.length) {
    loadProfSubTab(key, _profSubTab);
  }
}

function getProfTabs(key) {
  return {
    runist: [
      {id:'runes',     label:'✦ Runy'},
      {id:'my-runes',  label:'Moje rytiny'},
      {id:'forge',     label:'🔥 Výheň'},
      {id:'history',   label:'📜 Forge log'},
    ],
    oracle: [
      {id:'my-scrolls', label:'📜 Moje věštby'},
      {id:'scrolls',    label:'🔮 Trh věšteb'},
      {id:'accuracy',   label:'📊 Přesnost'},
      {id:'bonds',      label:'🌀 Pouta'},
      {id:'spirits',    label:'👻 Duchové'},
    ],
    broker: [
      {id:'bets',       label:'🎲 Sázky'},
      {id:'lotteries',  label:'🎟 Loterie'},
      {id:'shadow',     label:'🏠 Stínový dům'},
      {id:'ops',        label:'🕵 Operace'},
      {id:'identity',   label:'🎭 Identita'},
      {id:'targets',    label:'🎯 Cíle'},
    ],
  }[key] || [];
}

function switchProfTab(key, tabId, btn) {
  _profSubTab = tabId;
  document.querySelectorAll('.pr-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadProfSubTab(key, tabId);
}

async function loadProfSubTab(key, tabId) {
  const wrap = document.getElementById('prof-sub-content');
  if (!wrap) return;
  wrap.innerHTML = '<div class="pr-loading">Načítám...</div>';
  try {
    if (key === 'runist') {
      if (tabId === 'runes' || tabId === 'my-runes')   await renderRunosmithTab(wrap, tabId);
      else                                              await renderSoulforgerTab(wrap, tabId);
    } else if (key === 'oracle') {
      if (tabId === 'bonds' || tabId === 'spirits')     await renderFateweaverTab(wrap, tabId);
      else                                              await renderDivinerTab(wrap, tabId);
    } else if (key === 'broker') {
      if (tabId === 'ops' || tabId === 'identity' || tabId === 'targets') await renderAgentTab(wrap, tabId);
      else                                              await renderGamblerTab(wrap, tabId);
    }
  } catch(e) {
    wrap.innerHTML = `<div class="pr-error">${esc(e.message)}</div>`;
  }
}

function backToProfHub() {
  _profView = 'hub';
  renderProfHub(document.getElementById('prof-content'));
}

// ── PROFESSION ACTIONS ───────────────────────────────────────────────────────
async function learnProfession(key) {
  const meta = PROF_META[key] || {};
  try {
    await api('POST', '/professions/learn', { profession_key: key });
    _profData = await api('GET', '/professions/');
    toast(`⚗ Naučil ses profesi ${meta.name}!`, 's', 4000);
    addAct(`⚗ Nová profese: ${meta.name}`);
    renderProfDetail(document.getElementById('prof-content'), key);
  } catch(e) { toast(e.message, 'e'); }
}

// FIX: accepts slot parameter; sends { profession_key, replace_slot } as required by backend
async function activateProfession(key, slot) {
  const meta = PROF_META[key] || {};
  try {
    await api('POST', '/professions/activate', { profession_key: key, replace_slot: slot });
    _profData = await api('GET', '/professions/');
    toast(`⚡ ${meta.name} aktivována v slotu ${slot}!`, 's', 3000);
    renderProfDetail(document.getElementById('prof-content'), key);
  } catch(e) { toast(e.message, 'e'); }
}

// ══════════════════════════════════════════════════════════════════════════════
//  SUB-TAB RENDERS
// ══════════════════════════════════════════════════════════════════════════════

// ── RUNOVNÍK ──────────────────────────────────────────────────────────────────
async function renderRunosmithTab(wrap, tab) {
  if (tab === 'runes') {
    const d = await api('GET', '/runosmith/runes');
    const runes = d.runes || [];
    if (!runes.length) {
      wrap.innerHTML = `<div class="pr-hint">Žádné runy dostupné pro tvůj rank.</div>`;
      return;
    }

    // Group by tier
    const byTier = {};
    for (const r of runes) (byTier[r.tier] = byTier[r.tier] || []).push(r);

    const TIER_COL  = {1:'var(--common)',2:'var(--uncommon)',3:'var(--rare)',4:'var(--epic)',5:'var(--legend)'};
    const TIER_NAME = {1:'Základ',2:'Nižší magický',3:'Vyšší magický',4:'Vzácný',5:'Posvátný'};

    wrap.innerHTML = `
      <div class="pr-hint">Runy vyrývej v detailu itemu (Inventář → klikni item). Každý item má 2 runové sloty. Kombinace run tvoří synergie nebo konflikty.</div>
      ${Object.entries(byTier).map(([tier, rs]) => `
        <div class="pr-tier-hdr" style="color:${TIER_COL[tier]||'#fff'}">
          <span class="pr-tier-line"></span>Tier ${tier} · ${TIER_NAME[tier]||''}<span class="pr-tier-line"></span>
        </div>
        <div class="pr-rune-grid">
          ${rs.map(r => `
            <div class="pr-rune-card">
              <div class="pr-rune-ico" style="color:${TIER_COL[tier]||'#fff'}">${r.icon || '✦'}</div>
              <div class="pr-rune-name">${esc(r.name)}</div>
              <div class="pr-rune-effect">${esc(formatRuneEffect(r.effect))}</div>
              <div class="pr-rune-req">Rank ${r.rank_required}+</div>
            </div>`).join('')}
        </div>`).join('')}
    `;
  } else {
    wrap.innerHTML = `
      <div class="pr-hint">Přehled run vyrytých do tvých itemů je dostupný v <strong>Inventáři</strong> — klikni na item pro správu run a rezonanci.</div>
      <div class="pr-empty-state">✦<br><span>Otevři inventář</span></div>
    `;
  }
}

function formatRuneEffect(effect) {
  if (!effect || typeof effect !== 'object') return '—';
  const labels = { atk_bonus_pct:'ATK', def_bonus_pct:'DEF', hp_bonus_pct:'HP', spd_bonus:'SPD', luck_bonus:'LUCK', xp_bonus_pct:'XP' };
  return Object.entries(effect).map(([k,v]) => `+${v}${k.endsWith('_pct') ? '%' : ''} ${labels[k]||k}`).join(' · ');
}

// ── VĚŠTEC ────────────────────────────────────────────────────────────────────
async function renderDivinerTab(wrap, tab) {
  if (tab === 'my-scrolls') {
    const [d, questList] = await Promise.all([
      api('GET', '/diviner/my-scrolls'),
      api('GET', '/quest/list'),
    ]);
    const scrolls  = d.scrolls || [];
    const questOpts = (questList || []).map(q =>
      `<option value="${q.id}">${esc(q.icon || '')} ${esc(q.name)} (${q.difficulty})</option>`
    ).join('');
    wrap.innerHTML = `
      <div class="pr-hint">Tvoř věštby o výsledcích questů. Za správné předpovědi získáváš XP. Hráči mohou tvé svitky kupovat.</div>
      <button class="pr-inline-btn pr-inline-gold" onclick="togglePrForm('pr-form-scroll')">🔮 Nová věštba</button>
      <div id="pr-form-scroll" class="pr-form-card" style="display:none">
        <div class="pr-form-title">🔮 Vytvořit věštbu</div>
        <div class="pr-form-row"><label>Quest</label>
          <select id="sc-qid" class="pr-input">
            ${questOpts || '<option value="">— žádné questy k dispozici —</option>'}
          </select>
        </div>
        <div class="pr-form-row"><label>Typ věštby</label>
          <select id="sc-type" class="pr-input" onchange="updateScrollValueOptions()">
            <option value="quest_success">Úspěch questu</option>
            <option value="quest_drop_rarity">Rarita dropu</option>
          </select>
        </div>
        <div class="pr-form-row"><label>Předpovězená hodnota</label>
          <select id="sc-val" class="pr-input">
            <option value="success">Úspěch</option>
            <option value="fail">Neúspěch</option>
          </select>
        </div>
        <div class="pr-form-row"><label>Cena prodeje (G)</label><input type="number" id="sc-price" class="pr-input" min="1" placeholder="50"></div>
        <button class="btn btn-gold" onclick="createScroll()">🔮 Vytvořit</button>
      </div>
      ${!scrolls.length
        ? '<div class="pr-empty-state">📜<br><span>Žádné svitky</span></div>'
        : `<div class="pr-scroll-list">${scrolls.map(renderScrollCard).join('')}</div>`}
    `;
  } else if (tab === 'scrolls') {
    const d = await api('GET', '/diviner/scrolls');
    const scrolls = d.scrolls || [];
    wrap.innerHTML = `
      <div class="pr-hint">Kupuj svitky od jiných Věštců. Po ověření questu se dozvíš, zda Věštec uhádl správně.</div>
      ${!scrolls.length
        ? '<div class="pr-empty-state">🔮<br><span>Momentálně žádné svitky na prodeji</span></div>'
        : `<div class="pr-scroll-list">${scrolls.map(s => `
          <div class="pr-scroll-card">
            <div class="pr-scroll-header">
              <div class="pr-scroll-ico">🔮</div>
              <div style="flex:1">
                <div class="pr-scroll-quest">${esc(s.quest_name||`Quest #${s.quest_def_id}`)}</div>
                <div class="pr-scroll-meta">${esc(s.prediction_type)} · ${s.price} G</div>
              </div>
              <button class="pr-inline-btn pr-inline-gold" onclick="buyScroll(${s.id})">Koupit</button>
            </div>
          </div>`).join('')}`}
    `;
  } else if (tab === 'accuracy') {
    const d = await api('GET', '/diviner/accuracy');
    const pct = Math.round(d.accuracy_pct ?? 0);
    const col = pct >= 90 ? 'var(--gold2)' : pct >= 70 ? 'var(--green)' : 'var(--text2)';
    wrap.innerHTML = `
      <div class="pr-stat-block">
        <div class="pr-stat-big" style="color:${col}">${pct}%</div>
        <div class="pr-stat-lbl">Přesnost věšteb (týden)</div>
        <div class="pr-stat-sub">Ověřeno: ${d.week_verified||0} · Správně: ${d.week_correct||0}</div>
      </div>
      <div class="pr-threshold-list">
        <div class="pr-threshold ${pct>=70?'met':''}">🏆 70%+ přesnost — bonus XP každý týden</div>
        <div class="pr-threshold ${pct>=90?'met gold':''}">👑 90%+ přesnost — velký XP bonus</div>
      </div>
    `;
  }
}

function renderScrollCard(s) {
  const statusCol  = s.was_correct ? 'var(--green)' : s.is_verified ? 'var(--accent2)' : s.is_sold ? 'var(--gold2)' : 'var(--text3)';
  const statusText = s.was_correct ? '✓ Správně' : s.is_verified ? '✕ Špatně' : s.is_sold ? '⏳ Čeká na ověření' : '📜 Na prodeji';
  return `
    <div class="pr-scroll-card">
      <div class="pr-scroll-header">
        <div class="pr-scroll-ico">📜</div>
        <div style="flex:1">
          <div class="pr-scroll-quest">${esc(s.quest_name || `Quest #${s.quest_def_id}`)}</div>
          <div class="pr-scroll-meta">${esc(s.prediction_type)}: <em>${esc(String(s.prediction_value))}</em> · ${s.price} G</div>
        </div>
        <div style="color:${statusCol};font-family:'Cinzel',serif;font-size:0.68rem">${statusText}</div>
      </div>
    </div>`;
}

function togglePrForm(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function createScroll() {
  const body = {
    quest_def_id:     parseInt(document.getElementById('sc-qid')?.value),
    prediction_type:  document.getElementById('sc-type')?.value,
    prediction_value: document.getElementById('sc-val')?.value,
    price:            parseInt(document.getElementById('sc-price')?.value),
  };
  try {
    await api('POST', '/diviner/create', body);
    toast('🔮 Věštba vytvořena!', 's', 3000);
    await renderDivinerTab(document.getElementById('prof-sub-content'), 'my-scrolls');
  } catch(e) { toast(e.message, 'e'); }
}

// FIX: endpoint is POST /diviner/buy with body { scroll_id }, not path parameter
async function buyScroll(scrollId) {
  try {
    const d = await api('POST', '/diviner/buy', { scroll_id: scrollId });
    toast(`📜 Věštba odhalena: ${esc(String(d.prediction_value))}`, 'i', 5000);
    await renderDivinerTab(document.getElementById('prof-sub-content'), 'scrolls');
  } catch(e) { toast(e.message, 'e'); }
}

// ── DUŠEKOVAL ─────────────────────────────────────────────────────────────────
async function renderSoulforgerTab(wrap, tab) {
  if (tab === 'forge') {
    _forgeSelectedIds = [];
    const [d, invData] = await Promise.all([
      api('GET', '/soulforger/slots'),
      api('GET', '/inventory/'),
    ]);
    const slots = d.slots || [];
    const slotsHtml = slots.map((s, i) => {
      const busy  = !s.available && s.available_at && new Date(s.available_at) > new Date();
      const until = busy ? new Date(s.available_at).toLocaleString('cs', {hour:'2-digit',minute:'2-digit'}) : '';
      return `
        <div class="pr-forge-slot ${busy ? 'busy' : 'ready'}">
          <div class="pr-forge-slot-num">Slot ${i+1}</div>
          ${busy
            ? `<div class="pr-forge-ico-busy">🔥</div><div class="pr-forge-busy-txt">Tavení do ${until}</div>`
            : `<div class="pr-forge-ico-ready">◎</div><div class="pr-forge-ready-txt">Volný</div>`}
        </div>`;
    }).join('');

    const forgeable = (invData.items || []).filter(i => !i.equipped);
    const RC = {common:'var(--common)',uncommon:'var(--uncommon)',rare:'var(--rare)',epic:'var(--epic)',legendary:'var(--legend)'};
    const TI = {weapon:'⚔',helmet:'⛑',armor:'🛡',gloves:'🧤',boots:'👢',ring:'💍',amulet:'📿'};
    const itemsHtml = !forgeable.length
      ? '<div class="pr-empty-state" style="margin:12px 0">🗃<br><span>Inventář je prázdný nebo jsou všechny itemy nasazeny</span></div>'
      : forgeable.map(i => {
          const it  = i.item;
          const col = RC[it.rarity] || '#fff';
          return `
            <div class="pr-forge-item" onclick="toggleForgeItem(${i.id}, this)" title="${esc(it.name)} · ${esc(it.rarity)}">
              <div class="pr-forge-item-ico" style="color:${col}">${it.icon || TI[it.type] || '◆'}</div>
              <div class="pr-forge-item-name" style="color:${col}">${esc(it.name)}</div>
              <div class="pr-forge-item-meta">${esc(it.rarity)}</div>
            </div>`;
        }).join('');

    wrap.innerHTML = `
      <div class="pr-forge-slots-row">${slotsHtml}</div>
      <div class="pr-form-card" style="margin-top:14px">
        <div class="pr-form-title" style="color:var(--forge-col,#e07020)">🔥 Nové tavení</div>
        <div class="pr-form-row">
          <label>Vyber předměty (2–4 kliknutím)</label>
          <div class="pr-forge-item-grid">${itemsHtml}</div>
          <div class="pr-forge-sel-row">Vybráno: <span id="forge-sel-count">0</span> / 4</div>
        </div>
        <div class="pr-form-row">
          <label>Cíl tavení</label>
          <select id="forge-target-type" class="pr-input">
            <option value="weapon">Zbraň</option>
            <option value="armor">Brnění</option>
            <option value="helmet">Přilba</option>
            <option value="gloves">Rukavice</option>
            <option value="boots">Boty</option>
            <option value="ring">Prsten</option>
            <option value="amulet">Amulet</option>
          </select>
        </div>
        <button class="pr-inline-btn" style="background:linear-gradient(135deg,#3a1200,#803010);border-color:#e07020;color:#f09060" onclick="startForge()">🔥 Začít tavení</button>
      </div>
    `;
  } else {
    const d = await api('GET', '/soulforger/history');
    const logs = d.history || [];
    if (!logs.length) {
      wrap.innerHTML = '<div class="pr-empty-state">🔥<br><span>Zatím žádná tavení</span></div>';
      return;
    }
    const RC = {common:'var(--common)',uncommon:'var(--uncommon)',rare:'var(--rare)',epic:'var(--epic)',legendary:'var(--legend)'};
    wrap.innerHTML = `
      <div class="pr-forge-history">
        ${logs.map(l => `
          <div class="pr-forge-log">
            <div class="pr-forge-log-rarity" style="color:${RC[l.output_rarity]||'#fff'}">◆ ${l.output_rarity}</div>
            <div class="pr-forge-log-name">${esc(l.output_name||'?')}</div>
            ${l.output_flavor ? `<div class="pr-forge-log-flavor">${esc(l.output_flavor)}</div>` : ''}
            <div class="pr-forge-log-xp">+${l.base_xp} XP</div>
          </div>`).join('')}
      </div>`;
  }
}

async function startForge() {
  if (_forgeSelectedIds.length < 2) { toast('Vyber alespoň 2 předměty.', 'e'); return; }
  const targetType = document.getElementById('forge-target-type')?.value;
  try {
    const d = await api('POST', '/soulforger/forge', { inventory_item_ids: _forgeSelectedIds, target_type: targetType });
    toast(`🔥 Vykovano: ${esc(d.output_name)} (${d.output_rarity})`, 's', 5000);
    addAct(`🔥 Dušekoval: ${d.output_name}`);
    await renderSoulforgerTab(document.getElementById('prof-sub-content'), 'forge');
  } catch(e) { toast(e.message, 'e'); }
}

// ── ŠARLATÁN ──────────────────────────────────────────────────────────────────
async function renderGamblerTab(wrap, tab) {
  if (tab === 'bets') {
    const [d, questList] = await Promise.all([
      api('GET', '/gambler/bets'),
      api('GET', '/quest/list'),
    ]);
    const bets     = d.bets || [];
    const questOpts = (questList || []).map(q =>
      `<option value="${q.id}">${esc(q.icon || '')} ${esc(q.name)} (${q.difficulty})</option>`
    ).join('');
    wrap.innerHTML = `
      <div class="pr-hint">Uzavírej sázky s hráči nebo Stínovým domem. Max ${d.max_open||5} otevřených sázek najednou.</div>
      <button class="pr-inline-btn pr-inline-green" onclick="togglePrForm('pr-form-bet')">🎲 Nová sázka</button>
      <div id="pr-form-bet" class="pr-form-card" style="display:none">
        <div class="pr-form-title">🎲 Nová sázka</div>
        <div class="pr-form-row"><label>Protivník</label>
          <select id="bet-opponent" class="pr-input" onchange="toggleBetTarget()">
            <option value="npc">Stínový dům (NPC)</option>
            <option value="player">Hráč (PvP)</option>
          </select>
        </div>
        <div id="bet-target-row" style="display:none">
          <div class="pr-form-row"><label>Cílový hráč</label>${playerSearchHtml('bet-target', 'Hledat hráče...')}</div>
        </div>
        <div class="pr-form-row"><label>Typ sázky</label>
          <select id="bet-type" class="pr-input" onchange="onBetTypeChange()">
            <option value="quest_success">Výsledek questu (úspěch / neúspěch)</option>
            <option value="quest_drop_rarity">Rarita dropu z questu</option>
            <option value="arena_outcome">Výsledek arény</option>
          </select>
        </div>
        <div id="bet-quest-row" class="pr-form-row">
          <label>Quest</label>
          <select id="bet-quest-id" class="pr-input">
            ${questOpts || '<option value="">— žádné questy k dispozici —</option>'}
          </select>
        </div>
        <div class="pr-form-row"><label>Předpověď</label>
          <select id="bet-pred" class="pr-input">
            <option value="success">Úspěch</option>
            <option value="fail">Neúspěch</option>
          </select>
        </div>
        <div class="pr-form-row"><label>Vklad (min 100 G)</label><input type="number" id="bet-stake" class="pr-input" min="100" placeholder="500"></div>
        <button class="pr-inline-btn pr-inline-green" onclick="createBet()">Uzavřít sázku</button>
      </div>
      ${!bets.length
        ? '<div class="pr-empty-state">🎲<br><span>Žádné aktivní sázky</span></div>'
        : `<div class="pr-bet-list">${bets.map(b => renderBetCard(b)).join('')}</div>`}
    `;
  } else if (tab === 'lotteries') {
    const d = await api('GET', '/gambler/lotteries');
    const lots = d.lotteries || [];
    wrap.innerHTML = `
      <div class="pr-hint">Vytvoř loterii nebo se přidej do existující. Pool jde vítězi — Šarlatán bere organitázorský podíl.</div>
      <button class="pr-inline-btn pr-inline-gold" onclick="togglePrForm('pr-form-lot')">🎟 Nová loterie</button>
      <div id="pr-form-lot" class="pr-form-card" style="display:none">
        <div class="pr-form-title">🎟 Nová loterie</div>
        <div class="pr-form-row"><label>Vstupné (G)</label><input type="number" id="lot-fee" class="pr-input" min="10" placeholder="100"></div>
        <!-- FIX: backend expects draw_after_minutes (integer), not draw_at datetime -->
        <div class="pr-form-row"><label>Losování za (minuty)</label><input type="number" id="lot-draw" class="pr-input" min="60" placeholder="1440" title="Minuty od teď (min. 60)"></div>
        <button class="pr-inline-btn pr-inline-gold" onclick="createLottery()">Vytvořit loterii</button>
      </div>
      ${!lots.length
        ? '<div class="pr-empty-state">🎟<br><span>Žádné aktivní loterie</span></div>'
        : `<div class="pr-bet-list">${lots.map(renderLotteryCard).join('')}</div>`}
    `;
  } else {
    const d = await api('GET', '/gambler/shadow-house');
    const susp = d.suspicion_level || 0;
    wrap.innerHTML = `
      <div class="pr-hint">Stínový dům vždy přijme tvou sázku — ale bere 15 % z každé výhry. Opakované výhry zvyšují podezření a zhoršují kurzy.</div>
      <div class="pr-stat-block">
        <div class="pr-stat-big" style="color:var(--green)">${d.total_won||0} G</div>
        <div class="pr-stat-lbl">Celkem vyhráno od Stínového domu</div>
        <div class="pr-stat-sub">Sázek: ${d.total_bets||0} · Proher: ${d.total_losses||0}</div>
        ${susp > 0 ? `
          <div class="pr-suspicion-bar">
            <div class="pr-suspicion-label">Podezření <span style="color:var(--accent2)">${susp}/5</span></div>
            <div class="pr-xp-track"><div class="pr-xp-fill" style="width:${susp*20}%;background:var(--accent2)"></div></div>
            ${susp >= 4 ? '<div class="pr-suspicion-warn">⚠ Stínový dům tě sleduje — výrazně horší kurzy</div>' : ''}
          </div>` : ''}
      </div>
    `;
  }
}

function renderBetCard(b) {
  const SC = {open:'var(--text2)',accepted:'var(--gold2)',cancelled:'var(--text3)'};
  const statusColor = b.status === 'resolved'
    ? (b.result === 'win' ? 'var(--green)' : 'var(--accent2)')
    : (SC[b.status] || 'var(--text3)');
  const statusText = b.status === 'resolved'
    ? (b.result === 'win' ? '✓ Výhra' : '✕ Prohra')
    : b.status;
  return `
    <div class="pr-bet-card">
      <div class="pr-bet-ico">🎲</div>
      <div class="pr-bet-body">
        <div class="pr-bet-pred">${esc(b.bettor_prediction||'—')}</div>
        <div class="pr-bet-meta">${b.bettor_stake||0} G · ${b.is_vs_npc ? 'Stínový dům' : 'hráč vs hráč'}</div>
      </div>
      <div class="pr-bet-status" style="color:${statusColor}">${statusText}</div>
      ${b.status === 'open' && b.bettor_char_id !== char?.id
        ? `<button class="pr-inline-btn pr-inline-green" onclick="acceptBet(${b.id})">✓ Přijmout</button>` : ''}
    </div>`;
}

function renderLotteryCard(l) {
  return `
    <div class="pr-bet-card">
      <div class="pr-bet-ico">🎟</div>
      <div class="pr-bet-body">
        <div class="pr-bet-pred">Pool: ${l.pool_total||0} G · ${l.entry_count||0} účastníků</div>
        <div class="pr-bet-meta">Vstupné: ${l.entry_fee} G · ${new Date(l.draw_at).toLocaleDateString('cs')}</div>
      </div>
      <div class="pr-bet-status" style="color:var(--gold2)">${l.status}</div>
      ${l.status === 'open'
        ? `<button class="pr-inline-btn pr-inline-gold" onclick="enterLottery(${l.id})">🎟 Vstoupit</button>` : ''}
    </div>`;
}

async function createBet() {
  const betType  = document.getElementById('bet-type')?.value;
  const opponent = document.getElementById('bet-opponent')?.value;
  const isArena  = betType === 'arena_outcome';
  const subjectType = isArena ? 'arena' : 'quest';
  const subjectId   = isArena ? 0 : parseInt(document.getElementById('bet-quest-id')?.value || '0');
  if (!isArena && !subjectId) { toast('Vyber quest.', 'e'); return; }
  const targetVal    = document.getElementById('bet-target')?.value;
  const targetCharId = (opponent === 'player' && targetVal) ? parseInt(targetVal) : null;
  if (opponent === 'player' && !targetCharId) { toast('Vyber cílového hráče.', 'e'); return; }
  const body = {
    bet_type:       betType,
    subject_type:   subjectType,
    subject_id:     subjectId,
    stake:          parseInt(document.getElementById('bet-stake')?.value),
    prediction:     document.getElementById('bet-pred')?.value,
    target_char_id: targetCharId,
  };
  try { await api('POST', '/gambler/bet', body); toast('🎲 Sázka uzavřena!', 's', 3000); await renderGamblerTab(document.getElementById('prof-sub-content'), 'bets'); } catch(e) { toast(e.message, 'e'); }
}

async function acceptBet(id) {
  try { await api('POST', `/gambler/bet/${id}/accept`); toast('✓ Sázka přijata!', 's', 3000); await renderGamblerTab(document.getElementById('prof-sub-content'), 'bets'); } catch(e) { toast(e.message, 'e'); }
}

// FIX: backend expects draw_after_minutes (int), not draw_at (datetime string)
async function createLottery() {
  const body = {
    entry_fee:          parseInt(document.getElementById('lot-fee')?.value),
    draw_after_minutes: parseInt(document.getElementById('lot-draw')?.value),
  };
  try { await api('POST', '/gambler/lottery/create', body); toast('🎟 Loterie vytvořena!', 's', 3000); await renderGamblerTab(document.getElementById('prof-sub-content'), 'lotteries'); } catch(e) { toast(e.message, 'e'); }
}

async function enterLottery(id) {
  try { await api('POST', `/gambler/lottery/${id}/enter`); toast('🎟 Přihlášen!', 's', 3000); await renderGamblerTab(document.getElementById('prof-sub-content'), 'lotteries'); } catch(e) { toast(e.message, 'e'); }
}

// ── STÍNOVÝ AGENT ─────────────────────────────────────────────────────────────
async function renderAgentTab(wrap, tab) {
  if (tab === 'ops') {
    const d = await api('GET', '/agent/operations');
    const ops = d.operations || [];
    wrap.innerHTML = `
      <div class="pr-hint">Prováděj tajné operace na hráčích. Detekce = odhalení identity na 72 h. Rank snižuje šanci na odhalení.</div>
      <button class="pr-inline-btn pr-inline-purple" onclick="togglePrForm('pr-form-op')">🕵 Nová operace</button>
      <div id="pr-form-op" class="pr-form-card pr-form-dark" style="display:none">
        <div class="pr-form-title" style="color:var(--purple2)">🕵 Nová operace</div>
        <div class="pr-form-row"><label>Typ</label>
          <select id="op-type" class="pr-input">
            <option value="intel">Špionáž</option>
            <option value="sabotage">Sabotáž</option>
            <option value="steal">Krádež</option>
          </select>
        </div>
        <div class="pr-form-row"><label>Obtížnost</label>
          <select id="op-diff" class="pr-input">
            <option value="easy">Snadná</option>
            <option value="normal">Normální</option>
            <option value="hard">Těžká</option>
          </select>
        </div>
        <div class="pr-form-row"><label>Cíl (prázdné = Stínový dům)</label>${playerSearchHtml('op-target', 'volitelné...')}</div>
        <button class="pr-inline-btn pr-inline-purple" onclick="startOp()">Zahájit operaci</button>
      </div>
      ${!ops.length
        ? '<div class="pr-empty-state">🕵<br><span>Žádné operace</span></div>'
        : `<div class="pr-op-list">${ops.map(renderOpCard).join('')}</div>`}
    `;
  } else if (tab === 'identity') {
    const d = await api('GET', '/agent/identity');
    const id = d.identity;
    wrap.innerHTML = id ? `
      <div class="pr-identity-card">
        <div class="pr-identity-ico">🎭</div>
        <div class="pr-identity-body">
          <div class="pr-identity-pseudo">${esc(id.pseudonym)}</div>
          <div class="pr-identity-status ${id.is_revealed ? 'revealed' : 'safe'}">
            ${id.is_revealed ? `⚠ Odhalena do ${new Date(id.revealed_until).toLocaleDateString('cs')}` : '✓ Krytí zachováno'}
          </div>
          <div class="pr-identity-since">Krytí od: ${new Date(id.cover_maintained_since).toLocaleDateString('cs')}</div>
        </div>
      </div>
      <div style="margin-top:12px">
        <!-- FIX: pass desired enabled state so we can send { enabled: bool } to backend -->
        <button class="pr-inline-btn pr-inline-purple" onclick="toggleHardTarget(${!id.is_hard_target})">
          ${id.is_hard_target ? '🛡 Tvrdý cíl (aktivní) — klikni pro vypnutí' : '🛡 Stát se tvrdým cílem'}
        </button>
        <div class="pr-hint" style="margin-top:8px">Tvrdý cíl je obtížnější špehovat, ale upozorní útočníky na tvou ostražitost.</div>
      </div>
    ` : `<div class="pr-empty-state">🎭<br><span>Identita zatím nezaložena</span></div>`;
  } else {
    // FIX: backend returns { real_targets: [...], phantom_targets: [...] }, not { targets: [...] }
    const d = await api('GET', '/agent/targets');
    const realTargets    = d.real_targets    || [];
    const phantomTargets = d.phantom_targets || [];
    if (!realTargets.length && !phantomTargets.length) {
      wrap.innerHTML = '<div class="pr-empty-state">🎯<br><span>Žádní dostupní cíle</span></div>';
      return;
    }
    // FIX: phantom targets have `name` field; real targets have char_id, char_name, pseudonym
    const renderTarget = (t, isPhantom) => `
      <div class="pr-target-card ${isPhantom ? 'is-phantom' : ''}">
        <div class="pr-target-name">${isPhantom ? '👻 ' : ''}${esc(isPhantom ? (t.name || '???') : (t.pseudonym || t.char_name || '???'))}</div>
        ${!isPhantom ? `<div class="pr-target-meta">${esc(t.char_name)}</div>` : ''}
        ${!isPhantom ? `<div class="pr-target-id">ID: ${t.char_id}</div>` : ''}
      </div>`;
    wrap.innerHTML = `
      <div class="pr-hint">Hráči dostupní pro operace.</div>
      ${realTargets.length ? `
        <div class="pr-target-group-lbl">Reální hráči</div>
        <div class="pr-target-list">${realTargets.map(t => renderTarget(t, false)).join('')}</div>` : ''}
      ${phantomTargets.length ? `
        <div class="pr-target-group-lbl" style="margin-top:12px">Stínové cíle (Phantom)</div>
        <div class="pr-target-list">${phantomTargets.map(t => renderTarget(t, true)).join('')}</div>` : ''}
    `;
  }
}

// FIX: use o.operation_type (not o.op_type), o.finish_at (not o.collect_at)
function renderOpCard(o) {
  const SC = {active:'var(--gold2)',in_progress:'var(--gold2)',completed:'var(--green)',detected:'var(--accent)',failed:'var(--accent2)'};
  const canCollect = o.status === 'active' && o.finish_at && new Date(o.finish_at) <= new Date();
  return `
    <div class="pr-op-card">
      <div class="pr-op-ico">🕵</div>
      <div class="pr-op-body">
        <div class="pr-op-type">${esc(o.operation_type)} · ${esc(o.difficulty)}</div>
        <div class="pr-op-target">${o.target_name ? `→ ${esc(o.target_name)}` : 'Stínový dům'}</div>
      </div>
      <div class="pr-op-status" style="color:${SC[o.status]||'var(--text3)'}">${o.status}</div>
      ${canCollect ? `<button class="pr-inline-btn pr-inline-purple" onclick="collectOp(${o.id})">📦 Sebrat</button>` : ''}
    </div>`;
}

// FIX: operation_type (not op_type) to match StartOperationRequest schema
async function startOp() {
  const body = { operation_type: document.getElementById('op-type')?.value, difficulty: document.getElementById('op-diff')?.value, is_phantom: !document.getElementById('op-target')?.value };
  if (document.getElementById('op-target')?.value) body.target_char_id = parseInt(document.getElementById('op-target').value);
  try { await api('POST', '/agent/operations/start', body); toast('🕵 Operace zahájena!', 's', 3000); await renderAgentTab(document.getElementById('prof-sub-content'), 'ops'); } catch(e) { toast(e.message, 'e'); }
}

async function collectOp(id) {
  try {
    const d = await api('POST', `/agent/operations/${id}/collect`);
    toast(d.was_detected ? '⚠ Odhalení! Identita kompromitována.' : `✓ Úspěšná operace! +${d.xp_gained||0} XP`, d.was_detected ? 'e' : 's', 5000);
    await renderAgentTab(document.getElementById('prof-sub-content'), 'ops');
  } catch(e) { toast(e.message, 'e'); }
}

// FIX: accepts enabled boolean and sends { enabled } body as required by ToggleHardTargetRequest
async function toggleHardTarget(enabled) {
  try {
    const d = await api('POST', '/agent/identity/toggle-hard-target', { enabled: enabled });
    toast(d.is_hard_target ? '🛡 Tvrdý cíl aktivován' : '🛡 Tvrdý cíl deaktivován', 'i', 3000);
    await renderAgentTab(document.getElementById('prof-sub-content'), 'identity');
  } catch(e) { toast(e.message, 'e'); }
}

// ── TKADLEC OSUDU ─────────────────────────────────────────────────────────────
async function renderFateweaverTab(wrap, tab) {
  if (tab === 'bonds') {
    const d = await api('GET', '/fateweaver/bonds');
    const bonds    = d.bonds || [];
    const karma    = d.karma || 0;
    const karmaMax = d.karma_hard_cap || 10;
    const kPct     = Math.min(100, Math.round(karma / karmaMax * 100));
    const kCol     = karma >= karmaMax - 1 ? 'var(--accent2)' : karma >= karmaMax / 2 ? 'var(--gold2)' : 'var(--purple2)';
    const pl       = d.limits?.player_bonds || {};
    const sp       = d.limits?.spirit_bonds || {};

    wrap.innerHTML = `
      <div class="pr-karma-block">
        <div class="pr-karma-row">
          <span class="pr-karma-lbl">🌀 Karma</span>
          <span style="color:${kCol};font-family:'Cinzel',serif">${karma} / ${karmaMax}</span>
        </div>
        <div class="pr-xp-track"><div class="pr-xp-fill" style="width:${kPct}%;background:${kCol}"></div></div>
        ${karma >= karmaMax ? '<div class="pr-karma-blocked">⚠ Karma blokována — dokonči quest Smíření pro reset.</div>' : ''}
      </div>

      <div class="pr-limits-row">
        <div class="pr-limit-pill">🌀 Hráčská: ${pl.current||0}/${pl.max||3}</div>
        <div class="pr-limit-pill">👻 Duchová: ${sp.current||0}/${sp.max||2}</div>
      </div>

      <div style="display:flex;gap:8px;margin:12px 0">
        <button class="pr-inline-btn pr-inline-purple" onclick="togglePrForm('pr-form-bond-p')">🌀 Hráčské pouto</button>
        <button class="pr-inline-btn pr-inline-purple" onclick="togglePrForm('pr-form-bond-s')">👻 Pouto s duchem</button>
      </div>

      <div id="pr-form-bond-p" class="pr-form-card pr-form-dark" style="display:none">
        <div class="pr-form-title" style="color:var(--purple2)">🌀 Pouto mezi hráči</div>
        <div class="pr-form-row"><label>Hráč A</label>${playerSearchHtml('bond-a')}</div>
        <div class="pr-form-row"><label>Hráč B</label>${playerSearchHtml('bond-b')}</div>
        <div class="pr-form-row"><label>Typ pouta</label>
          <select id="bond-type" class="pr-input">
            <option value="cooperation">Spolupráce (+10% XP)</option>
            <option value="war_pact">Válečný pakt (+12% ATK)</option>
            <option value="curse">Prokletí (−8% quest šance cíle)</option>
            <option value="guild_bond">Cechovní pouto (+6% XP/ATK)</option>
          </select>
        </div>
        <button class="pr-inline-btn pr-inline-purple" onclick="createBond('player')">Vytvořit pouto</button>
      </div>

      <div id="pr-form-bond-s" class="pr-form-card pr-form-dark" style="display:none">
        <div class="pr-form-title" style="color:var(--purple2)">👻 Pouto s duchem</div>
        <div class="pr-form-row"><label>Cílový hráč</label>${playerSearchHtml('bond-target')}</div>
        <div class="pr-form-row"><label>Typ ducha</label>
          <select id="spirit-type" class="pr-input">
            <option value="warrior">Válečník (+ATK)</option>
            <option value="mage">Mág (+MPen)</option>
            <option value="ranger">Lovec (+SPD)</option>
          </select>
        </div>
        <button class="pr-inline-btn pr-inline-purple" onclick="createBond('spirit')">Přivolat ducha</button>
      </div>

      ${!bonds.length
        ? '<div class="pr-empty-state">🌀<br><span>Žádná aktivní pouta</span></div>'
        : `<div class="pr-bond-list">${bonds.map(renderBondCard).join('')}</div>`}
    `;
  } else {
    const d = await api('GET', '/fateweaver/spirits');
    const spirits = d.spirits || [];
    wrap.innerHTML = `
      <div class="pr-hint">Duchové jsou NPC entity. Efekt je slabší než u hráčských pout, ale nevyžadují souhlas druhého hráče.</div>
      <div class="pr-spirit-grid">
        ${spirits.map(s => `
          <div class="pr-spirit-card">
            <div class="pr-spirit-ico">${s.icon||'👻'}</div>
            <div class="pr-spirit-name">${esc(s.name)}</div>
            <div class="pr-spirit-desc">${esc(s.description||'')}</div>
          </div>`).join('')}
      </div>`;
  }
}

function renderBondCard(b) {
  const TC = {cooperation:'var(--green)',war_pact:'var(--accent2)',curse:'var(--purple2)',guild_bond:'var(--gold2)',ancestral:'var(--text2)'};
  const col = TC[b.bond_type] || 'var(--text2)';
  return `
    <div class="pr-bond-card" style="--bcol:${col}">
      <div class="pr-bond-type" style="color:${col}">🌀 ${esc(b.bond_type)}</div>
      <div class="pr-bond-targets">${esc(b.target_a_name||'?')} ↔ ${esc(b.target_b_name||'—')}</div>
      <div class="pr-bond-meta">Fire: ${b.fire_count||0} · Dní aktivní: ${b.days_active||0}</div>
      <button class="pr-inline-btn" style="background:rgba(184,32,48,.15);border-color:var(--accent);color:var(--accent2);margin-top:7px" onclick="dissolveBond(${b.id})">✕ Rozváže</button>
    </div>`;
}

async function createBond(type) {
  let body, endpoint;
  if (type === 'player') {
    const idA = parseInt(document.getElementById('bond-a')?.value);
    const idB = parseInt(document.getElementById('bond-b')?.value);
    if (!idA) { toast('Vyber Hráče A ze seznamu.', 'e'); return; }
    if (!idB) { toast('Vyber Hráče B ze seznamu.', 'e'); return; }
    body = { target_a_char_id: idA, target_b_char_id: idB, bond_type: document.getElementById('bond-type')?.value };
    endpoint = '/fateweaver/bond/player';
  } else {
    const idT = parseInt(document.getElementById('bond-target')?.value);
    if (!idT) { toast('Vyber cílového hráče ze seznamu.', 'e'); return; }
    body = { target_char_id: idT, spirit_type: document.getElementById('spirit-type')?.value };
    endpoint = '/fateweaver/bond/spirit';
  }
  try { await api('POST', endpoint, body); toast('🌀 Pouto vytvořeno!', 's', 3000); await renderFateweaverTab(document.getElementById('prof-sub-content'), 'bonds'); } catch(e) { toast(e.message, 'e'); }
}

async function dissolveBond(id) {
  try { await api('DELETE', `/fateweaver/bond/${id}`); toast('Pouto rozvázáno.', 'i', 3000); await renderFateweaverTab(document.getElementById('prof-sub-content'), 'bonds'); } catch(e) { toast(e.message, 'e'); }
}

// ── SDÍLENÉ HELPERY PRO FORMULÁŘE PROFESÍ ────────────────────────────────────

// Věštec: aktualizuje select pro předpovídanou hodnotu podle typu věštby
function updateScrollValueOptions() {
  const type = document.getElementById('sc-type')?.value;
  const sel  = document.getElementById('sc-val');
  if (!sel) return;
  if (type === 'quest_drop_rarity') {
    sel.innerHTML = `
      <option value="common">Common (Obyčejný)</option>
      <option value="uncommon">Uncommon (Neobvyklý)</option>
      <option value="rare">Rare (Vzácný)</option>
      <option value="epic">Epic (Epický)</option>
      <option value="legendary">Legendary (Legendární)</option>`;
  } else {
    sel.innerHTML = `
      <option value="success">Úspěch</option>
      <option value="fail">Neúspěch</option>`;
  }
}

// Šarlatán: přepíná viditelnost výběru hráče (PvP vs Shadow House)
function toggleBetTarget() {
  const opponent = document.getElementById('bet-opponent')?.value;
  const row = document.getElementById('bet-target-row');
  if (row) row.style.display = opponent === 'player' ? 'block' : 'none';
}

// Šarlatán: aktualizuje select předpovědi a viditelnost quest-row dle typu sázky
function onBetTypeChange() {
  const betType  = document.getElementById('bet-type')?.value;
  const questRow = document.getElementById('bet-quest-row');
  const predSel  = document.getElementById('bet-pred');
  if (questRow) questRow.style.display = betType === 'arena_outcome' ? 'none' : '';
  if (!predSel) return;
  if (betType === 'quest_drop_rarity') {
    predSel.innerHTML = `
      <option value="common">Common (Obyčejný)</option>
      <option value="uncommon">Uncommon (Neobvyklý)</option>
      <option value="rare">Rare (Vzácný)</option>
      <option value="epic">Epic (Epický)</option>
      <option value="legendary">Legendary (Legendární)</option>`;
  } else if (betType === 'arena_outcome') {
    predSel.innerHTML = `
      <option value="win">Výhra</option>
      <option value="lose">Prohra</option>`;
  } else {
    predSel.innerHTML = `
      <option value="success">Úspěch</option>
      <option value="fail">Neúspěch</option>`;
  }
}

// Dušekoval: přepíná výběr itemu pro tavení (klik = select/deselect)
function toggleForgeItem(invItemId, el) {
  const idx = _forgeSelectedIds.indexOf(invItemId);
  if (idx >= 0) {
    _forgeSelectedIds.splice(idx, 1);
    el.classList.remove('is-selected');
  } else {
    if (_forgeSelectedIds.length >= 4) { toast('Maximálně 4 předměty.', 'e'); return; }
    _forgeSelectedIds.push(invItemId);
    el.classList.add('is-selected');
  }
  const cnt = document.getElementById('forge-sel-count');
  if (cnt) cnt.textContent = _forgeSelectedIds.length;
}
