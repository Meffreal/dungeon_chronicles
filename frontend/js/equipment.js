// ── VYBAVENÍ ──────────────────────────────────────────────────────────────
// Achievement title cache — avoids re-fetching on every equip page open
let _achTitleCache = null;
let _achTitleCacheAt = 0;
const ACH_CACHE_TTL = 120_000; // 2 minutes

const BONUS_TAG = {atk:'ATK',def:'ARMOR',spd:'SPD',str:'STR',dex:'AQI',int:'INT',end:'HP',luck:'LUCK',hp:'HP',mp:'MP'};

const SLOTS = [
  {k:'helmet'},{k:'armor'},
  {k:'gloves'},{k:'ring'},
  {k:'amulet'},{k:'boots'},
  {k:'weapon'},
];

function openEquippedItemDetail(slot) {
  const item = char.equipment?.[slot];
  if (!item) return;
  const inv = invData.find(i => i.item?.id === item.id);
  if (inv) {
    openItemDetail(inv);
  } else {
    openItemDetail({ id: -1, item, quantity: 1, equipped: true, equipped_in: slot });
  }
}

async function renderEquip() {
  if (!char) return;
  const eq = char.equipment || {};

  showLoading('equip-layout');

  // Načti dostupné tituly z odemčených achievementů (with TTL cache)
  let availableTitles = [];
  try {
    const now = Date.now();
    if (!_achTitleCache || now - _achTitleCacheAt > ACH_CACHE_TTL) {
      const achData = await api('GET', '/achievements/');
      _achTitleCache = Object.values(achData.categories)
        .flat()
        .filter(a => a.unlocked && a.title)
        .map(a => a.title);
      _achTitleCacheAt = now;
    }
    availableTitles = _achTitleCache;
  } catch(e) {}

  const slot = s => {
    const item = eq[s.k];
    const has = !!item;

    // Transmog: pokud je nastaven, zobraz kosmetický vzhled
    const tmog = char.equipment_transmog?.[s.k];
    const displayItem = tmog || item;  // kosmetický item, nebo skutečný
    const hasTmog = !!tmog && !!item;  // transmog aktivní jen pokud je slot plný

    const rc = has ? (RARITY_COL[(hasTmog ? tmog : item)?.rarity] || '#9d9d9d') : 'var(--border)';
    const bonusChips = has
      ? Object.entries(item.bonuses || {})  // bonusy vždy ze skutečného itemu!
          .filter(([,v]) => v > 0)
          .map(([k,v]) => `<span class="eq-slot-bonus-chip">+${v} ${BONUS_TAG[k]||k.toUpperCase()}</span>`)
          .join('')
      : '';
    const invObj = has && typeof invData !== 'undefined' ? (invData || []).find(i => i.item?.id === item.id) : null;
    const dur = invObj?.durability ?? 100;
    const durCol = dur >= 50 ? '#1eff00' : dur >= 25 ? '#ff8c00' : '#ff4040';
    const durBar = has ? `<div class="eq-slot-dur-bar" title="Trvanlivost: ${dur}%"><div style="width:${dur}%;background:${durCol};height:100%;border-radius:2px;transition:width .3s"></div></div>` : '';

    // Transmog badge + tlačítko
    const tmogBadge = hasTmog
      ? `<div class="eq-tmog-badge" title="Transmog: ${esc(tmog.name)} (skutečný: ${esc(item.name)})">🎨</div>`
      : '';
    const tmogBtn = has
      ? `<button class="eq-tmog-btn" onclick="event.stopPropagation();openTransmogModal('${s.k}')" title="Nastav transmog pro ${SLOT_CZ[s.k]}">🎨</button>`
      : '';

    return `<div class="eq-slot eq-mslot-${s.k} ${has?'filled':''} ${hasTmog?'eq-slot-transmogged':''}" style="--slot-rc:${rc}"
              data-slot-key="${s.k}"
              onclick="${has ? `openEquippedItemDetail('${s.k}')` : ''}">
      <div class="eq-slot-icon" style="${has ? `filter:drop-shadow(0 3px 10px ${rc}88)` : ''}">${has ? (hasTmog ? tmog.icon : item.icon) : SLOT_ICONS[s.k]}</div>
      <div class="eq-slot-body">
        <div class="eq-slot-type">${SLOT_CZ[s.k]}</div>
        <div class="eq-slot-name" style="color:${rc}">${has ? esc(hasTmog ? tmog.name : item.name) : 'Prázdné'}</div>
        ${has && bonusChips
          ? `<div class="eq-slot-bonuses">${bonusChips}</div>`
          : `<div class="eq-slot-empty-hint">${has ? '—' : 'Slot prázdný'}</div>`}
        ${durBar}
      </div>
      ${tmogBadge}
      ${tmogBtn}
      ${has ? `<div class="rarity-pip" style="background:${rc}" title="${RARITY_CZ[(hasTmog?tmog:item).rarity]||''}"></div>` : ''}
    </div>`;
  };

  // ── Kompaktní čtvercový slot pro oltářní layout ──────────────────────
  const altarSlot = sk => {
    const item = eq[sk];
    const has = !!item;
    const tmog = char.equipment_transmog?.[sk];
    const hasTmog = !!tmog && !!item;
    const rc = has ? (RARITY_COL[(hasTmog ? tmog : item)?.rarity] || '#9d9d9d') : 'rgba(150,95,20,.22)';
    const icon = has ? (hasTmog ? tmog.icon : item.icon) : SLOT_ICONS[sk];
    const name = has ? esc(hasTmog ? tmog.name : item.name) : '';
    return `<div class="altar-slot altar-slot-${sk} ${has?'filled':''} ${hasTmog?'altar-slot-transmogged':''}"
      style="--slot-rc:${rc}"
      data-slot-key="${sk}"
      onclick="${has ? `openEquippedItemDetail('${sk}')` : ''}">
      <div class="altar-slot-frame">
        <div class="altar-slot-icon">${icon}</div>
        ${has ? `<div class="altar-rarity-pip" style="background:${rc}"></div>` : ''}
        ${hasTmog ? `<div class="altar-tmog-pip" title="Transmog aktivní">🎨</div>` : ''}
      </div>
      <div class="altar-slot-type">${SLOT_CZ[sk]}</div>
      ${has ? `<div class="altar-slot-name" style="color:${rc}">${name}</div>` : ''}
    </div>`;
  };

  const titleSelectorHtml = `
    <div class="title-selector">
      <div class="title-current" onclick="toggleTitlePicker()">
        ${char.current_title
          ? `<span class="char-title">[${esc(char.current_title)}]</span>`
          : '<span class="title-none">Žádný titul</span>'}
        <span class="title-arrow">▾</span>
      </div>
      <div class="title-list hidden" id="title-list">
        <div class="title-option ${!char.current_title ? 'active' : ''}"
             onclick="selectTitle(null)">— Žádný titul —</div>
        ${availableTitles.map(t =>
          `<div class="title-option ${char.current_title === t ? 'active' : ''}"
               onclick="selectTitle('${t.replace(/'/g, "\\'")}')">${esc(t)}</div>`
        ).join('')}
      </div>
    </div>`;

  // Sestav HTML pro aktivní set bonusy
  const setActive = Object.values(char.set_bonuses?.active || {});
  const setBonusPanelHtml = setActive.length > 0
    ? `<div class="equip-set-panel">
        <div class="equip-set-panel-title">✦ Aktivní sady</div>
        ${setActive.map(s => {
          const need3 = Math.max(0, 3 - s.pieces_equipped);
          const need5 = Math.max(0, 5 - s.pieces_equipped);
          const prog3 = need3 > 0 ? `<span class="set-need">ještě ${need3} pro bonus</span>` : '';
          const prog5 = need5 > 0 ? `<span class="set-need">ještě ${need5} pro bonus</span>` : '';
          return `
          <div class="equip-set-entry" style="--set-color:${s.color}">
            <div class="equip-set-name">${s.badge} ${esc(s.set_name)}</div>
            <div class="equip-set-pieces">${s.pieces_equipped} / 5 kusů</div>
            <div class="equip-set-bonuses">
              <div class="equip-set-bonus-row ${s.bonus_3pc_active?'active':'inactive'}">
                <span>3 kusy: ${esc(s.bonus_3pc_desc)}</span>
                ${s.bonus_3pc_active ? '<span class="set-check">✓</span>' : prog3}
              </div>
              <div class="equip-set-bonus-row ${s.bonus_5pc_active?'active':'inactive'}">
                <span>5 kusů: ${esc(s.bonus_5pc_desc)}</span>
                ${s.bonus_5pc_active ? '<span class="set-check">✓</span>' : prog5}
              </div>
            </div>
          </div>`;
        }).join('')}
      </div>`
    : '';

  // Repair-all button — zobraz pokud je alespoň jeden nasazený item poškozený
  const equippedInvItems = SLOTS.map(s => (invData || []).find(i => i.item?.id === eq[s.k]?.id)).filter(Boolean);
  const totalRepairCost = equippedInvItems.reduce((sum, i) => sum + Math.max(0, (100 - (i.durability ?? 100)) * 3), 0);
  const repairAllBtn = totalRepairCost > 0
    ? `<button class="equip-repair-btn" onclick="repairAll()">🔧 Opravit vše (${totalRepairCost} G)</button>`
    : '';

  const sp = char.stat_points || 0;

  const statPointsBanner = sp > 0
    ? `<div class="equip-sp-banner">⬆ <strong>${sp}</strong> ${sp === 1 ? 'bod' : sp < 5 ? 'body' : 'bodů'} k přidělení</div>`
    : '';

  document.getElementById('equip-layout').innerHTML = `
    ${statPointsBanner}

    <div class="equip-altar">
      <!-- ── Oltářní 3 sloupce: sloty | portrét | sloty ── -->
      <div class="altar-cols">

        <!-- Levý sloupec: Přilba · Brnění · Rukavice -->
        <div class="altar-col-slots altar-col-left">
          ${altarSlot('helmet')}
          ${altarSlot('armor')}
          ${altarSlot('gloves')}
        </div>

        <!-- Střed: Portrét + info -->
        <div class="altar-col-center">
          <div class="altar-portrait-zone">
            <div class="altar-portrait-frame">
              <img id="equip-avatar-img" src="${getAvatarUrl(char.appearance, char.id)}" alt="Character Avatar" class="altar-portrait-img">
              <div id="equip-avatar-fallback" style="display:none;position:absolute;inset:0;align-items:center;justify-content:center;background:linear-gradient(135deg,#4ECDC4,#45B7D1);border-radius:4px;font-size:3rem;color:white;z-index:2">🧙</div>
            </div>
            <button class="altar-edit-btn" onclick="openAppearanceModal()" title="Upravit vzhled postavy">✏</button>
          </div>
          <div class="altar-char-info">
            <div class="altar-char-name">${esc(char.name)}</div>
            <div class="altar-char-lvl">Level ${char.level} · ${CLS_N[char.cls]}</div>
            ${typeof getFactionBadgeHtml === 'function' ? getFactionBadgeHtml(char.faction, factionData?.reputation) : ''}
            ${titleSelectorHtml}
          </div>
        </div>

        <!-- Pravý sloupec: Amulet · Prsten · Boty -->
        <div class="altar-col-slots altar-col-right">
          ${altarSlot('amulet')}
          ${altarSlot('ring')}
          ${altarSlot('boots')}
        </div>

      </div><!-- /altar-cols -->

      <!-- Zbraň — full width pod oltářem -->
      <div class="altar-weapon-row">
        ${slot({k:'weapon'})}
      </div>

      ${setBonusPanelHtml}

      <div class="equip-actions">
        ${repairAllBtn}
        ${Object.keys(char.equipment_transmog || {}).length > 0
          ? `<button class="equip-repair-btn" onclick="clearAllTransmogs()" style="background:rgba(147,51,234,.12);border-color:rgba(147,51,234,.4);color:#c084fc">🎨 Zrušit všechny transmoogy</button>`
          : ''}
      </div>
    </div><!-- /equip-altar -->`;

  renderStatPanel();
  
  // Setup avatar error handling
  const avatarImg = document.getElementById('equip-avatar-img');
  if (avatarImg) {
    avatarImg.onerror = function() {
      console.error('[Equipment] Avatar failed to load');
      this.style.display = 'none';
      const fallback = document.getElementById('equip-avatar-fallback');
      if (fallback) fallback.style.display = 'flex';
    };
    
    avatarImg.onload = function() {
      console.log('[Equipment] Avatar loaded successfully');
      const fallback = document.getElementById('equip-avatar-fallback');
      if (fallback) fallback.style.display = 'none';
    };
  }

  _registerTipContainer('equip-layout', '.eq-slot.filled, .altar-slot.filled', card => {
    const sk = card.dataset.slotKey;
    if (!sk) return null;
    const item = char?.equipment?.[sk];
    if (!item) return null;
    const inv = (typeof invData !== 'undefined' ? invData : []).find(i => i.equipped && i.item?.type === sk)
      || { item, upgrade_level: 0, durability: 100 };
    return inv;
  });
}

// ── STAT PANEL renderer ────────────────────────────────────────────────────
function renderStatPanel() {
  if (!char) return;
  if (!document.getElementById('stat-panel')) return;
  renderTalents();

  const eq  = char.stats_breakdown?.eq_bonus ?? {};
  const com = char.combat ?? {};

  // ── Zdroje ──
  const hpMax  = com.hp_max ?? 0;
  const hpEq   = eq.hp ?? 0;
  const hpBase = hpMax - hpEq;

  document.getElementById('sp-hp-val').textContent  = hpMax.toLocaleString('cs');
  document.getElementById('sp-hp-base').textContent = hpBase.toLocaleString('cs');
  document.getElementById('sp-hp-eq').textContent   = hpEq > 0 ? `+${hpEq.toLocaleString('cs')} vybavení` : '';

  // ── Základní atributy ──
  const PRIMARY_STAT = { warrior:'strength', mage:'intelligence', ranger:'dexterity' };
  const primaryKey   = PRIMARY_STAT[char.cls] || '';

  // Klíč v eq_bonus: str/dex/int/end/luck — mapujeme z plného jména
  const EQ_KEY = { strength:'str', dexterity:'dex', intelligence:'int', endurance:'end', luck:'luck' };

  // ATTR_SVG je globální konstanta definovaná v ui.js
  const ATTR_DEF = [
    { key:'strength',     ico: ATTR_SVG.strength,     lbl:'Strength',     col:'c-red',    tip:'Warrior primary. ATK = weapon × (1 + STR/10) + DEX/2 + INT/2. Soft cap: 0–50 100% | 51–150 70% | 151+ 30%' },
    { key:'dexterity',    ico: ATTR_SVG.dexterity,    lbl:'Dexterity',    col:'c-green',  tip:'Ranger primary. ATK = weapon × (1 + DEX/10) + STR/2 + INT/2. Also determines SPD = soft_cap(DEX). Soft cap: 0–50 100% | 51–150 70% | 151+ 30%' },
    { key:'intelligence', ico: ATTR_SVG.intelligence, lbl:'Intelligence', col:'c-blue',   tip:'Mage primary. ATK = weapon × (1 + INT/10) + STR/2 + DEX/2. Soft cap: 0–50 100% | 51–150 70% | 151+ 30%' },
    { key:'endurance',    ico: ATTR_SVG.endurance,    lbl:'Endurance',    col:'c-gold',   tip:'HP = END × class_mult × (level + 1). Class mult: Warrior 4 | Ranger 3 | Mage 2' },
    { key:'luck',         ico: ATTR_SVG.luck,         lbl:'Luck',         col:'c-purple', tip:'Crit chance = min(50%, LUCK / (enemy_level × 4)). Crit deals 175% damage.' },
  ];

  const sp = char.stat_points || 0;

  // Calculate max stat value across all attrs for relative bar width
  const allStatVals = ATTR_DEF.map(a => char.stats?.[a.key] ?? 0);
  const maxStatVal  = Math.max(1, ...allStatVals);

  document.getElementById('sp-attrs').innerHTML = ATTR_DEF.map(a => {
    const base    = char.stats?.[a.key] ?? 0;
    const eqBonus = eq[EQ_KEY[a.key]]   ?? 0;
    const total   = base + eqBonus;
    const isPrim  = a.key === primaryKey;
    const barPct  = Math.round((total / maxStatVal) * 100);
    const basePct = Math.round((base  / maxStatVal) * 100);

    const capWarn = total > 150
      ? `<span class="sp-attr-cap-warn zone3" title="Heavy diminishing returns above 150 (30% efficiency)">⚠⚠</span>`
      : total > 50
        ? `<span class="sp-attr-cap-warn" title="Diminishing returns above 50 (70% efficiency)">⚠</span>`
        : '';

    return `<div class="sp-attr-card${isPrim ? ' primary-attr' : ''}" id="sp-attr-${a.key}" title="${a.tip}">
      <div class="sp-attr-top">
        <span class="sp-attr-ico">${a.ico}</span>
        <span class="sp-attr-lbl">${a.lbl}${isPrim ? ' ★' : ''}</span>
        <span class="sp-attr-val ${a.col}">${total}</span>
        ${capWarn}
        ${sp > 0 ? `<button class="stat-alloc-btn" onclick="allocStat('${a.key}', event)" title="Add 1 point to ${a.lbl}">+</button>` : ''}
      </div>
      <div class="sp-attr-bar-track">
        <div class="sp-attr-bar-base" style="width:${basePct}%"></div>
        ${eqBonus > 0 ? `<div class="sp-attr-bar-eq" style="width:${barPct}%;"></div>` : ''}
      </div>
      <div class="sp-bd">
        <span class="sp-bd-base">Base <strong>${base}</strong></span>
        ${eqBonus > 0 ? `<span class="sp-bd-eq">+${eqBonus} eq</span>` : ''}
      </div>
    </div>`;
  }).join('');

  // ── Damage Range ──
  const CLASS_WEAPON_BASE = { warrior: 8, ranger: 6, mage: 5 };
  const SUBCLASS_DMG_MULT = {
    berserker: 1.30, guardian: 0.90,
    elementalist: 1.25, necromancer: 0.85,
    sharpshooter: 1.20, shadowblade: 0.95,
  };
  const softCap = v => {
    if (v <= 50)  return v;
    if (v <= 150) return 50 + (v - 50)  * 0.7;
    return 50 + 100 * 0.7 + (v - 150) * 0.3;
  };

  const eqItems  = char.equipment || {};
  const weaponDmg = eqItems.weapon?.bonuses?.atk || CLASS_WEAPON_BASE[char.cls] || 5;

  // Sum eq stat bonuses ze všech slotů
  let eqStr = 0, eqDex = 0, eqInt = 0;
  for (const item of Object.values(eqItems)) {
    if (!item?.bonuses) continue;
    eqStr += item.bonuses.str || 0;
    eqDex += item.bonuses.dex || 0;
    eqInt += item.bonuses.int || 0;
  }

  const totStr = (char.strength     || 0) + eqStr;
  const totDex = (char.dexterity    || 0) + eqDex;
  const totInt = (char.intelligence || 0) + eqInt;

  const scStr = softCap(totStr), scDex = softCap(totDex), scInt = softCap(totInt);
  let primary, secA, secB;
  if      (char.cls === 'warrior') { primary = scStr; secA = scDex; secB = scInt; }
  else if (char.cls === 'ranger')  { primary = scDex; secA = scStr; secB = scInt; }
  else                             { primary = scInt; secA = scStr; secB = scDex; }

  const baseDmg = weaponDmg * (1 + primary / 10) + secA / 2 + secB / 2;

  let dmgMult = SUBCLASS_DMG_MULT[char.subclass] || 1.0;
  const talents = char.talents || [];
  if (talents.includes('mana_surge')) dmgMult *= 1.15;

  const minDmg = Math.floor(baseDmg * dmgMult * 0.85);
  const maxDmg = Math.floor(baseDmg * dmgMult * 1.15);

  const critMult = talents.includes('battle_rage') ? 2.0 : 1.75;
  const critMin  = Math.floor(minDmg * critMult);
  const critMax  = Math.floor(maxDmg * critMult);

  const dmgTip = `Base: weapon(${weaponDmg}) × (1 + primary/10) + sec/2\nVariance: ±15%${char.subclass ? `\nSubclass: ×${SUBCLASS_DMG_MULT[char.subclass] || 1.0}` : ''}${talents.includes('mana_surge') ? '\nMana Surge: ×1.15' : ''}\nCrit (×${critMult}): ${critMin} – ${critMax}`;

  document.getElementById('sp-combat').innerHTML = `
    <div class="sp-dmg-card" title="${dmgTip}">
      <div class="sp-dmg-label">
        <svg class="sp-attr-svg" viewBox="0 0 16 16" fill="none">
          <path d="M3 13L13 3M10 3h3v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="4.5" cy="11.5" r="1.5" fill="currentColor" opacity=".6"/>
        </svg>
        Damage
      </div>
      <div class="sp-dmg-range">
        <span class="sp-dmg-min">${minDmg}</span>
        <span class="sp-dmg-sep">–</span>
        <span class="sp-dmg-max">${maxDmg}</span>
      </div>
      <div class="sp-dmg-crit">${ATTR_SVG.crit} Crit: ${critMin} – ${critMax}</div>
    </div>`;

  // Vyčisti případný starý ability element
  const abilityEl = document.getElementById('sp-ability');
  if (abilityEl) abilityEl.innerHTML = '';
}

// ── TALENT TREE ──────────────────────────────────────────────────────────────
const TALENT_DEFS = {
  warrior: [
    { key:'fortitude',   name:'Odolnost',          emoji:'🧱', level_req:10, desc:'+15 % max HP.' },
    { key:'battle_rage', name:'Válečná Zuřivost',  emoji:'😤', level_req:20, desc:'+25 % poškození při critu.' },
    { key:'iron_skin',   name:'Železná Kůže',      emoji:'🛡️', level_req:30, desc:'-20 % přijatého poškození.' },
  ],
  mage: [
    { key:'arcane_focus', name:'Arkánné Soustředění', emoji:'🔮', level_req:10, desc:'+20 % dmg speciální schopnosti.' },
    { key:'mana_surge',   name:'Příval Many',          emoji:'💧', level_req:20, desc:'+25 % max many.' },
    { key:'spell_echo',   name:'Ozvěna Kouzla',        emoji:'✨', level_req:30, desc:'25% šance opakovat schopnost za 60 %.' },
  ],
  ranger: [
    { key:'eagle_eye',    name:'Orlí Zrak',     emoji:'🦅', level_req:10, desc:'+8 LUCK (crit šance).' },
    { key:'evasion',      name:'Úskok',          emoji:'💨', level_req:20, desc:'+10 % šance na dodge.' },
    { key:'hunters_mark', name:'Lovecká Značka', emoji:'🎯', level_req:30, desc:'První útok +75 % dmg.' },
  ],
};

const TALENT_T2_DEFS = {
  warrior: [
    { key:'cyclone_strike', name:'Cyklónový Úder', emoji:'🌪', desc:'Každé 4. kolo: 3 údery × 50% ATK.' },
    { key:'rallying_cry',   name:'Bojový Pokřik',  emoji:'📯', desc:'Každé 4. kolo: +15% HP obnova + štít 2 kola.' },
    { key:'execute',        name:'Poprava',         emoji:'⚰', desc:'Každé 4. kolo: pod 25% HP nepřítele → 3× ATK.' },
  ],
  mage: [
    { key:'arcane_storm',  name:'Arkánná Bouře',   emoji:'⚡', desc:'Každé 4. kolo: 3 kouzla × 60% dmg, pierce.' },
    { key:'mana_void',     name:'Prázdnota Many',  emoji:'🕳', desc:'Každé 4. kolo: vysaje 30% many nepřítele.' },
    { key:'time_warp',     name:'Časový Zlom',     emoji:'⏳', desc:'Každé 4. kolo: druhý útok za 80% dmg.' },
  ],
  ranger: [
    { key:'rain_of_arrows', name:'Déšť Šípů',      emoji:'🏹', desc:'Každé 4. kolo: 4 šípy × 40% ATK + bleed.' },
    { key:'shadow_step',    name:'Stínový Krok',   emoji:'👤', desc:'Každé 4. kolo: 80% dodge + protiútok.' },
    { key:'mark_for_death', name:'Označení Smrtí', emoji:'🎯', desc:'Každé 4. kolo: trvale -25% DEF nepřítele.' },
  ],
};

function renderTalents() {
  const el = document.getElementById('sp-talents');
  if (!el || !char) return;
  const defs    = TALENT_DEFS[char.cls] || [];
  const unlocked = new Set(char.talents || []);
  el.innerHTML = defs.map(t => {
    const isUnlocked = unlocked.has(t.key);
    return `
      <div class="talent-card ${isUnlocked ? 'talent-unlocked' : 'talent-locked'}">
        <div class="talent-card-emoji">${isUnlocked ? t.emoji : '🔒'}</div>
        <div class="talent-card-info">
          <div class="talent-card-name">${t.name} <span class="talent-lvl">Lv.${t.level_req}</span></div>
          <div class="talent-card-desc">${t.desc}</div>
        </div>
        <div class="talent-card-badge">${isUnlocked ? '✓' : `≥${t.level_req}`}</div>
      </div>`;
  }).join('');

  // ── T2 sekce ───────────────────────────────────────────────────────────────
  const t2el = document.getElementById('sp-t2-section');
  if (!t2el) return;
  const t2defs = TALENT_T2_DEFS[char.cls] || [];
  const chosenT2 = char.talent_t2 || null;
  const level = char.level || 0;

  if (level < 25) {
    // Locked state
    t2el.innerHTML = `
      <div class="t2-section-header">⚔ Tier 2 — Aktivní Schopnost</div>
      <div class="t2-locked-msg">
        🔒 Odemkne se na <strong>levelu 25</strong>. Aktuální level: ${level}.
      </div>`;
  } else if (chosenT2) {
    // Chosen (read-only)
    const chosen = t2defs.find(t => t.key === chosenT2) || { emoji:'?', name: chosenT2, desc:'' };
    t2el.innerHTML = `
      <div class="t2-section-header">⚔ Tier 2 — Aktivní Schopnost</div>
      <div class="t2-chosen-card">
        <div class="t2-chosen-emoji">${chosen.emoji}</div>
        <div class="t2-chosen-info">
          <div class="t2-chosen-name">${chosen.name} <span class="t2-chosen-badge">🔒 Zvoleno</span></div>
          <div class="t2-chosen-desc">${chosen.desc}</div>
        </div>
      </div>`;
  } else {
    // Choose cards
    const cardsHtml = t2defs.map(t => `
      <div class="t2-card">
        <div class="t2-card-emoji">${t.emoji}</div>
        <div class="t2-card-name">${t.name}</div>
        <div class="t2-card-desc">${t.desc}</div>
        <button class="t2-choose-btn" onclick="chooseT2Talent('${t.key}', '${t.name.replace(/'/g,"\\'")}')">Zvolit</button>
      </div>`).join('');
    t2el.innerHTML = `
      <div class="t2-section-header">⚔ Tier 2 — Aktivní Schopnost</div>
      <div class="t2-choose-header">
        Zvol svou aktivní schopnost — <span class="t2-choose-warn">tato volba je TRVALÁ</span>
      </div>
      <div class="t2-cards-grid">${cardsHtml}</div>`;
  }
}

async function chooseT2Talent(key, name) {
  if (!confirm(`Opravdu chceš zvolit "${name}"?\n\nTato volba je TRVALÁ a nelze ji změnit.`)) return;
  try {
    const c = await api('POST', '/character/choose-t2', { t2_key: key });
    updateUI(c);
    await renderEquip();
    toast(`T2 talent zvolen: ${name}`, 's', 4000);
  } catch(e) { toast(e.message || 'Chyba při výběru T2 talentu', 'e'); }
}

function switchSpTab(tabId, btn) {
  if (tabId === 'talents') renderTalents();
  ['stats','spells','talents'].forEach(id => {
    const el = document.getElementById('sp-tab-' + id);
    if (el) el.style.display = id === tabId ? '' : 'none';
  });
  document.querySelectorAll('.sp-tab').forEach(b => b.classList.remove('sp-tab-active'));
  if (btn) btn.classList.add('sp-tab-active');
}

function toggleTitlePicker() {
  document.getElementById('title-list')?.classList.toggle('hidden');
}

async function selectTitle(title) {
  try {
    const c = await api('POST', '/character/set-title', { title });
    updateUI(c);
    await renderEquip();
    toast(title ? `Titul nastaven: [${title}]` : 'Titul odložen', 'i', 2000);
  } catch(e) { toast(e.message, 'e'); }
}

async function unequipSlot(slot) {
  try {
    const d = await api('POST', '/inventory/unequip', { slot });
    const itemName = char.equipment?.[slot]?.name || SLOT_CZ[slot];
    toast(`Sundáno: ${itemName}`, 'i', 2000);
    updateUI(d.character);
    renderEquip();
    await loadInventory();
    addAct(`🔓 Sundáno: ${itemName}`);
  } catch(e) { toast(e.message, 'e'); }
}

// ── APPEARANCE AVATAR HELPERS ─────────────────────────────────────────────
function getAppearanceAvatar(appearance) {
  if (!appearance) return CLS_E[char?.cls] || '⚔';
  
  // Emoji variace na základě vzhledu
  const skinTone = appearance.skin_tone || 0;
  const isFantasy = skinTone > 4; // Fantasy barvy jsou indexy 5+
  
  if (isFantasy) {
    // Fantazijní postavy - speciální emoji
    if (char?.cls === 'mage') return '🧙';
    if (char?.cls === 'ranger') return '🏹';
    return '👤';
  }
  
  // Normální postavy dle třídy + vzhledu
  const hasBeard = (appearance.facial_hair || 0) > 0;
  
  if (char?.cls === 'warrior') {
    return hasBeard ? '🧔' : '👨';
  }
  if (char?.cls === 'mage') {
    return '🧙';
  }
  if (char?.cls === 'ranger') {
    return appearance.hair_style === 4 ? '👩' : '🏹'; // Holá dívka vs lučištnice
  }
  
  return CLS_E[char?.cls] || '⚔';
}

