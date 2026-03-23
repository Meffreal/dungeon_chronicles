// ── COMBAT BUILD PAGE ──────────────────────────────────────────────────────
// Agregovaný pohled na celý bojový build: strategie + specializace + talenty
// + efektivní statistiky + dungeon modifikátor + set bonusy + shrnutí.
// Žádný nový backend — kombinuje char global + /dungeon/modifier.

const BUILD_TALENTS = {
  warrior: [
    { key:'fortitude',   lvl:10, emoji:'🧱', name:'Odolnost',          desc:'+15 % max HP' },
    { key:'battle_rage', lvl:20, emoji:'😤', name:'Válečná Zuřivost',  desc:'+25 % poškození při critu' },
    { key:'iron_skin',   lvl:30, emoji:'🛡️', name:'Železná Kůže',      desc:'−20 % přijatého fyzického poškození' },
  ],
  mage: [
    { key:'arcane_focus', lvl:10, emoji:'🔮', name:'Arkánné Soustředění', desc:'+20 % poškození schopností' },
    { key:'mana_surge',   lvl:20, emoji:'💧', name:'Příval Many',         desc:'+25 % max MP' },
    { key:'spell_echo',   lvl:30, emoji:'✨', name:'Ozvěna Kouzla',       desc:'25 % šance zopakovat schopnost za 60 % poškození' },
  ],
  ranger: [
    { key:'eagle_eye',    lvl:10, emoji:'🦅', name:'Orlí Zrak',       desc:'+8 LUCK (šance na kritický zásah)' },
    { key:'evasion',      lvl:20, emoji:'💨', name:'Úskok',            desc:'+10 % základní šance na vyhnutí' },
    { key:'hunters_mark', lvl:30, emoji:'🎯', name:'Lovecká Značka',  desc:'+75 % poškození prvním útokem v souboji' },
  ],
};

const BUILD_SUBCLASSES = {
  berserker:    { name:'Berserkr',       cls:'warrior', emoji:'🔴', mults:[{stat:'DMG',v:+30},{stat:'Armor',v:-15}] },
  guardian:     { name:'Strážce',        cls:'warrior', emoji:'🛡️', mults:[{stat:'Armor',v:+35},{stat:'HP',v:+20},{stat:'DMG',v:-10}] },
  elementalist: { name:'Elementalista', cls:'mage',    emoji:'☄️', mults:[{stat:'DMG',v:+25},{stat:'Armor',v:-10}] },
  necromancer:  { name:'Nekromancer',   cls:'mage',    emoji:'☠️', mults:[{stat:'DMG',v:-15}] },
  sharpshooter: { name:'Ostrostřelec',  cls:'ranger',  emoji:'💥', mults:[{stat:'DMG',v:+10},{stat:'LUCK',v:+20},{stat:'Armor',v:-10}] },
  shadowblade:  { name:'Stínová Čepel', cls:'ranger',  emoji:'🌑', mults:[{stat:'Crit DMG',v:+35},{stat:'LUCK',v:+10},{stat:'DMG',v:-5},{stat:'Armor',v:-10}] },
};


const BUILD_RADAR_AXES = [
  { key:'atk',  lbl:'ATK',  max:200 },
  { key:'spd',  lbl:'SPD',  max:80  },
  { key:'mp',   lbl:'MP',   max:400 },
  { key:'luck', lbl:'LUCK', max:60  },
  { key:'def',  lbl:'DEF',  max:160 },
];

// ── Combat stat výpočet (mirror backend logiky) ────────────────────────────
function _computeCombatStats(c) {
  const eq    = c.stats_breakdown?.eq_bonus ?? {};
  const stats = c.stats ?? {};
  const eqItems = c.equipment || {};
  const sc = v => v <= 50 ? v : v <= 150 ? 50 + (v - 50) * 0.7 : 120 + (v - 150) * 0.3;

  const totStr  = (stats.strength     ?? 0) + (eq.str  ?? 0);
  const totDex  = (stats.dexterity    ?? 0) + (eq.dex  ?? 0);
  const totInt  = (stats.intelligence ?? 0) + (eq.int  ?? 0);
  const totLuck = (stats.luck         ?? 0) + (eq.luck ?? 0);

  const WPN_BASE = { warrior: 8, ranger: 6, mage: 5 };
  const weaponDmg = eqItems.weapon?.bonuses?.atk || WPN_BASE[c.cls] || 5;

  let prim, secA, secB;
  if (c.cls === 'warrior')     { prim = sc(totStr); secA = sc(totDex) / 2; secB = sc(totInt) / 2; }
  else if (c.cls === 'ranger') { prim = sc(totDex); secA = sc(totStr) / 2; secB = sc(totInt) / 2; }
  else                         { prim = sc(totInt); secA = sc(totStr) / 2; secB = sc(totDex) / 2; }

  const SUB_MULT = { berserker:1.10, guardian:0.95, elementalist:1.15, necromancer:1.00, sharpshooter:1.10, shadowblade:1.12 };
  const talents = c.talents || [];
  const dmgMult = (SUB_MULT[c.subclass] || 1.0) * (talents.includes('mana_surge') ? 1.15 : 1.0);

  const atk  = Math.round((weaponDmg * (1 + prim / 10) + secA + secB) * dmgMult);
  const def  = Object.entries(eqItems).filter(([s]) => s !== 'weapon').reduce((sum, [, item]) => sum + (item?.bonuses?.def || 0), 0);
  const spd  = Math.round(sc(totDex));
  const hp   = c.combat?.hp_max ?? 0;
  const mp   = c.cls === 'mage' ? Math.round(hp * 0.30) : 0;
  const luck = totLuck;

  return { atk, def, spd, hp, mp, luck };
}

// ── Hlavní load ────────────────────────────────────────────────────────────
async function loadBuild() {
  const root = document.getElementById('build-root');
  if (!root) return;
  root.innerHTML = '<div class="loading-state"><span class="loading-spinner"></span><span>Načítám build...</span></div>';
  const modRes = await api('GET', '/dungeon/modifier').catch(() => null);
  _renderBuild(modRes);
}

// ── Render ─────────────────────────────────────────────────────────────────
function _renderBuild(modRes) {
  const root = document.getElementById('build-root');
  if (!root || !char) { if (root) root.innerHTML = '<div class="empty-state">🔒 Nejprve vytvoř postavu.</div>'; return; }

  const c       = char;
  const talents = c.talents || [];
  const sub     = c.subclass ? BUILD_SUBCLASSES[c.subclass] : null;
  const combat  = c.combat  || {};
  const sets    = c.set_bonuses || {};
  const mod     = modRes?.modifier || null;

  const cs = _computeCombatStats(c);
  const radarStats = {
    atk:  cs.atk,
    def:  cs.def,
    spd:  cs.spd,
    mp:   cs.mp,
    luck: cs.luck,
  };

  root.innerHTML = `
    <div class="page-hdr">🏗 Bojový Build</div>

    <div class="build-top-row">
      <div class="build-section build-radar-section">
        <div class="build-sec-title">📊 Profil silných stránek</div>
        ${_bRadarSvg(radarStats)}
      </div>
    </div>

    <div class="build-mid-row">
      <div class="build-section">
        <div class="build-sec-title">🌟 Specializace</div>
        ${_bSubclassCard(sub, c.cls, c.level)}
      </div>
      <div class="build-section">
        <div class="build-sec-title">✨ Talent strom</div>
        ${_bTalentTree(c.cls, c.level, talents)}
      </div>
    </div>

    <div class="build-section">
      <div class="build-sec-title">⚡ Efektivní statistiky v souboji</div>
      ${_bEffStats(cs)}
    </div>

    ${Object.keys(sets).length ? `<div class="build-section">${_bSetBonuses(sets)}</div>` : ''}
    ${mod ? `<div class="build-section">${_bModBanner(mod)}</div>` : ''}

    <div class="build-section build-summary-sec">
      <div class="build-sec-title">💡 Co to znamená v boji</div>
      <p class="build-summary-text">${_bSummary(c, talents, sub)}</p>
    </div>`;
}


// ── Specializace karta ─────────────────────────────────────────────────────
function _bSubclassCard(sub, cls, level) {
  if (!sub) {
    const locked = level < 10;
    return `<div class="build-no-sub">
      ${locked
        ? `🔒 Dostupná od level 10 <span class="build-lock-note">(ještě ${10 - level} úrovní)</span>`
        : `⚠️ Specializace není zvolena — <a class="build-link" onclick="showPage('subclass');loadSubclass()">Zvol specializaci →</a>`
      }
    </div>`;
  }
  const pos = sub.mults.filter(m => m.v > 0);
  const neg = sub.mults.filter(m => m.v < 0);
  return `<div class="build-sub-card">
    <div class="build-sub-head">
      <span class="build-sub-emoji">${sub.emoji}</span>
      <div>
        <div class="build-sub-name">${sub.name}</div>
        <div class="build-sub-cls">${CLS_N[sub.cls] || sub.cls}</div>
      </div>
    </div>
    <div class="build-sub-mults">
      ${pos.map(m => `<span class="build-mult pos">+${m.v}% ${m.stat}</span>`).join('')}
      ${neg.map(m => `<span class="build-mult neg">${m.v}% ${m.stat}</span>`).join('')}
    </div>
  </div>`;
}

// ── Talent strom ───────────────────────────────────────────────────────────
function _bTalentTree(cls, level, unlocked) {
  const talents = BUILD_TALENTS[cls] || [];
  return `<div class="build-talent-row">${talents.map((t, i) => {
    const isUnlocked = unlocked.includes(t.key);
    const canUnlock  = !isUnlocked && level >= t.lvl;
    const isLocked   = level < t.lvl;
    const cls2 = isUnlocked ? 'bt-unlocked' : canUnlock ? 'bt-available' : 'bt-locked';
    return `
      ${i > 0 ? '<div class="build-tconn"></div>' : ''}
      <div class="build-tnode ${cls2}" title="${t.name}: ${t.desc}">
        <div class="bt-emoji">${isLocked ? '🔒' : t.emoji}</div>
        <div class="bt-name">${t.name}</div>
        <div class="bt-lvl">Lv.${t.lvl}</div>
        <div class="bt-desc">${t.desc}</div>
      </div>`;
  }).join('')}</div>`;
}

// ── Efektivní statistiky ───────────────────────────────────────────────────
function _bEffStats(cs) {
  const rows = [
    { ico:'⚔',  lbl:'Útok (ATK)',    val: cs.atk  ?? 0 },
    { ico:'🛡',  lbl:'Obrana (DEF)',  val: cs.def  ?? 0 },
    { ico:'💨',  lbl:'Rychlost (SPD)',val: cs.spd  ?? 0 },
    { ico:'❤',   lbl:'Max HP',        val: cs.hp   ?? 0 },
    { ico:'🍀',  lbl:'Štěstí (LUCK)', val: cs.luck ?? 0 },
  ];
  return `<div class="build-stats-grid">${rows.map(r => `<div class="build-stat-row">
      <span class="bsr-ico">${r.ico}</span>
      <span class="bsr-lbl">${r.lbl}</span>
      <span class="bsr-raw">${r.val}</span>
    </div>`).join('')}</div>`;
}

// ── Set bonusy ─────────────────────────────────────────────────────────────
function _bSetBonuses(sets) {
  const entries = Object.entries(sets);
  return `<div class="build-sec-title">✦ Aktivní set bonusy</div>
    <div class="build-sets-list">${entries.map(([name, info]) =>
      `<div class="build-set-row">
        <span class="build-set-name">✦ ${esc(name)}</span>
        <span class="build-set-info">${info.pieces_equipped ?? '?'} dílů — ${esc(info.bonus_desc ?? 'Aktivní')}</span>
      </div>`
    ).join('')}</div>`;
}

// ── Dungeon modifikátor ────────────────────────────────────────────────────
function _bModBanner(mod) {
  return `<div class="build-sec-title">🏰 Aktivní dungeon modifikátor</div>
    <div class="build-mod-row" style="border-left-color:${mod.color || 'var(--accent)'}">
      <span class="build-mod-emoji">${mod.emoji || '🏰'}</span>
      <div>
        <div class="build-mod-name">${esc(mod.name)}</div>
        <div class="build-mod-desc">${esc(mod.description)}</div>
      </div>
    </div>`;
}

// ── Radar SVG ──────────────────────────────────────────────────────────────
function _bRadarSvg(stats) {
  const cx = 90, cy = 95, R = 62, S = 190;
  const n  = BUILD_RADAR_AXES.length;
  const angles = BUILD_RADAR_AXES.map((_, i) => -Math.PI / 2 + i * (2 * Math.PI / n));
  const _pt = (a, r) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const _poly = (r) => angles.map(a => _pt(a, r).map(v => v.toFixed(1)).join(',')).join(' ');

  const grids = [0.33, 0.66, 1].map(p =>
    `<polygon points="${_poly(R * p)}" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="1"/>`
  ).join('');

  const axisLines = angles.map(a => {
    const [x, y] = _pt(a, R);
    return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(255,255,255,.12)" stroke-width="1"/>`;
  }).join('');

  const valPts = angles.map((a, i) => {
    const ax  = BUILD_RADAR_AXES[i];
    const pct = Math.min(1, (stats[ax.key] || 0) / ax.max);
    return _pt(a, R * pct).map(v => v.toFixed(1)).join(',');
  }).join(' ');

  const dots = angles.map((a, i) => {
    const ax  = BUILD_RADAR_AXES[i];
    const pct = Math.min(1, (stats[ax.key] || 0) / ax.max);
    const [x, y] = _pt(a, R * pct);
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="var(--accent2)" stroke="none"/>`;
  }).join('');

  const labels = angles.map((a, i) => {
    const ax = BUILD_RADAR_AXES[i];
    const [x, y] = _pt(a, R + 16);
    return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle" fill="var(--text2)" font-size="9.5" font-family="Cinzel,serif">${ax.lbl}</text>`;
  }).join('');

  return `<div class="build-radar-wrap">
    <svg width="${S}" height="${S}" viewBox="0 0 ${S} ${S}">
      ${grids}${axisLines}
      <polygon points="${valPts}" fill="rgba(30,127,184,.28)" stroke="var(--accent)" stroke-width="1.8"/>
      ${dots}${labels}
    </svg>
  </div>`;
}

// ── Plain-language shrnutí ─────────────────────────────────────────────────
function _bSummary(c, talents, sub) {
  const clsName = CLS_N[c.cls] || c.cls;
  const subName = sub?.name || null;

  const tFx = [];
  if (talents.includes('fortitude'))    tFx.push('vyšší HP');
  if (talents.includes('iron_skin'))    tFx.push('redukce fyzického poškození');
  if (talents.includes('battle_rage'))  tFx.push('silné kritické zásahy');
  if (talents.includes('arcane_focus')) tFx.push('silnější schopnosti');
  if (talents.includes('mana_surge'))   tFx.push('velká zásobárna many');
  if (talents.includes('spell_echo'))   tFx.push('ozvěna kouzel');
  if (talents.includes('eagle_eye'))    tFx.push('vysoká šance na crit');
  if (talents.includes('evasion'))      tFx.push('úskok');
  if (talents.includes('hunters_mark')) tFx.push('smrtící první útok');

  let text = subName
    ? `Tvůj <strong>${clsName}</strong> (${subName}).`
    : `Tvůj <strong>${clsName}</strong>.`;
  if (tFx.length) text += ` Talenty přidávají: ${tFx.join(', ')}.`;

  // Specifické kombinace
  if (c.subclass === 'guardian' && talents.includes('iron_skin'))
    text += ' ⚠️ Strážce + Železná Kůže = extrémně tvrdá kombinace. Útok bude nízký, ale přežiješ skoro vše.';
  else if (c.subclass === 'berserker')
    text += ' 🔥 Berserkr = maximální útok. Způsobíš hodně, ale i dostaneš hodně.';
  else if (c.subclass === 'elementalist')
    text += ' ☄️ Elementalista — silné útočné schopnosti s armor penetrací.';
  else if (c.subclass === 'necromancer')
    text += ' ☠️ Nekromancer — nižší přímý útok, ale schopnost Mor Nemrtvých probíjí 100% obrany a aplikuje jed + krvácení + oslabení najednou. Silný v delších soubojích.';
  else if (c.subclass === 'shadowblade')
    text += ' 🌑 Stínová Čepel — dvojitý úder s garantovaným krvácením a zvýšeným crit poškozením.';
  else if (c.subclass === 'sharpshooter' && talents.includes('hunters_mark'))
    text += ' 🎯 Ostrostřelec s Loveckou Značkou — první útok způsobí +75 % bonus. Smrtící sestava na jeden výstřel.';

  return text;
}
