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
    { key:'eagle_eye',    lvl:10, emoji:'🦅', name:'Eagle Eye',       desc:'+8 LUCK (šance na kritický zásah)' },
    { key:'evasion',      lvl:20, emoji:'💨', name:'Evasion',            desc:'+10 % základní šance na vyhnutí' },
    { key:'hunters_mark', lvl:30, emoji:'🎯', name:"Hunter's Mark",  desc:'+75 % poškození prvním útokem v souboji' },
  ],
};

const BUILD_SUBCLASSES = {
  berserker:    { name:'Berserkr',       cls:'warrior', emoji:'🔴', mults:[{stat:'ATK',v:+30},{stat:'DEF',v:-15}] },
  guardian:     { name:'Strážce',        cls:'warrior', emoji:'🛡️', mults:[{stat:'DEF',v:+35},{stat:'HP',v:+20},{stat:'ATK',v:-10}] },
  elementalist: { name:'Elementalista', cls:'mage',    emoji:'☄️', mults:[{stat:'ATK',v:+25},{stat:'MP',v:+15},{stat:'DEF',v:-10}] },
  necromancer:  { name:'Nekromancer',   cls:'mage',    emoji:'☠️', mults:[{stat:'MP',v:+30},{stat:'SPD',v:+10},{stat:'ATK',v:-15}] },
  sharpshooter: { name:'Ostrostřelec',  cls:'ranger',  emoji:'💥', mults:[{stat:'ATK',v:+20},{stat:'LUCK',v:+30},{stat:'DEF',v:-10}] },
  shadowblade:  { name:'Stínová Čepel', cls:'ranger',  emoji:'🌑', mults:[{stat:'SPD',v:+35},{stat:'ATK',v:-5},{stat:'DEF',v:-10}] },
};


const BUILD_RADAR_AXES = [
  { key:'atk',  lbl:'ATK',  max:200 },
  { key:'spd',  lbl:'SPD',  max:80  },
  { key:'mp',   lbl:'MP',   max:400 },
  { key:'luck', lbl:'LUCK', max:60  },
  { key:'def',  lbl:'DEF',  max:160 },
];

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

  const radarStats = {
    atk:  combat.eff_atk ?? combat.atk  ?? 0,
    def:  combat.eff_def ?? combat.def  ?? 0,
    spd:  combat.eff_spd ?? combat.spd  ?? 0,
    mp:   combat.mp_max  ?? 0,
    luck: combat.luck    ?? 0,
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
      ${_bEffStats(combat)}
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
function _bEffStats(combat) {
  const rows = [
    { ico:'⚔',  lbl:'Útok (ATK)',    raw: combat.atk    ?? 0, eff: combat.eff_atk ?? combat.atk ?? 0 },
    { ico:'🛡',  lbl:'Obrana (DEF)',  raw: combat.def    ?? 0, eff: combat.eff_def ?? combat.def ?? 0 },
    { ico:'💨',  lbl:'Rychlost (SPD)',raw: combat.spd    ?? 0, eff: combat.eff_spd ?? combat.spd ?? 0 },
    { ico:'❤',   lbl:'Max HP',        raw: combat.hp_max ?? 0, eff: combat.hp_max  ?? 0 },
    { ico:'🍀',  lbl:'Štěstí (LUCK)', raw: combat.luck   ?? 0, eff: combat.luck    ?? 0 },
  ];
  return `<div class="build-stats-grid">${rows.map(r => {
    const capped = r.eff < r.raw;
    return `<div class="build-stat-row">
      <span class="bsr-ico">${r.ico}</span>
      <span class="bsr-lbl">${r.lbl}</span>
      <span class="bsr-raw">${r.raw}</span>
      ${capped ? `<span class="bsr-sep">→ cap:</span><span class="bsr-eff">${r.eff}</span>` : ''}
    </div>`;
  }).join('')}</div>`;
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
    text += ' ☄️ Elementalista — silné útočné schopnosti.';
  else if (c.subclass === 'shadowblade')
    text += ' 🌑 Stínová Čepel — vysoká rychlost zajišťuje první kolo.';
  else if (c.subclass === 'sharpshooter' && talents.includes('hunters_mark'))
    text += ' 🎯 Ostrostřelec s Loveckou Značkou — první útok způsobí +75 % bonus. Smrtící sestava na jeden výstřel.';

  return text;
}
