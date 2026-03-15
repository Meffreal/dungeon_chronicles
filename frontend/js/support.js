// ── PODPORA HRY (Transparency & Anti-predatory declaration) ───────────────────

let _supportData = null;

async function loadSupport() {
  const root = document.getElementById('support-root');
  if (!root) return;
  if (_supportData) { _renderSupport(_supportData); return; }

  try {
    const d = await api('GET', '/crystals/transparency');
    _supportData = d;
    _renderSupport(d);
  } catch(e) {
    root.innerHTML = `<div class="empty-state">⚠️ Nepodařilo se načíst data.</div>`;
  }
}

function _renderSupport(d) {
  const root = document.getElementById('support-root');
  if (!root) return;

  root.innerHTML = `
    ${_renderHero()}
    ${_renderCommitments(d.commitments)}
    ${_renderCrystalSources(d.crystal_sources, d.shop_items)}
    ${_renderDropRates(d.drop_rates)}
    ${_renderMechanics(d)}
  `;
}

function _renderHero() {
  return `
    <div class="sup-hero">
      <div class="sup-hero-icon">💚</div>
      <div class="sup-hero-title">Podpora hry</div>
      <div class="sup-hero-sub">
        Dungeon Chronicles je <strong>free-to-play</strong> hra navržená s respektem k hráčům.
        Tato stránka transparentně ukazuje, jak funguje monetizace a herní mechaniky.
      </div>
      <div class="sup-hero-badge">
        <span class="sup-badge sup-badge-green">✓ Žádné pay-to-win</span>
        <span class="sup-badge sup-badge-blue">✓ Transparentní šance</span>
        <span class="sup-badge sup-badge-purple">✓ Žádné lootboxy</span>
      </div>
    </div>`;
}

function _renderCommitments(commitments) {
  if (!commitments?.length) return '';
  const cards = commitments.map(c => `
    <div class="sup-commit-card">
      <div class="sup-commit-icon">${c.icon}</div>
      <div class="sup-commit-body">
        <div class="sup-commit-title">${esc(c.title)}</div>
        <div class="sup-commit-desc">${esc(c.desc)}</div>
      </div>
    </div>`).join('');

  return `
    <div class="sup-section">
      <div class="sup-section-hdr">📜 Naše závazky k hráčům</div>
      <div class="sup-commit-grid">${cards}</div>
    </div>`;
}

function _renderCrystalSources(sources, shopItems) {
  const sourceRows = (sources || []).map(s => `
    <div class="sup-earn-row">
      <span class="sup-earn-icon">${s.icon}</span>
      <span class="sup-earn-source">${esc(s.source)}</span>
      <span class="sup-earn-amt">${esc(s.amount)}</span>
    </div>`).join('');

  const shopRows = (shopItems || []).map(i => `
    <div class="sup-shop-row">
      <span class="sup-shop-emoji">${i.emoji}</span>
      <span class="sup-shop-name">${esc(i.name)}</span>
      <span class="sup-shop-cost">💎 ${i.cost}</span>
      <span class="sup-shop-type sup-type-${i.type}">${_typeLabel(i.type)}</span>
    </div>`).join('');

  return `
    <div class="sup-section">
      <div class="sup-section-hdr">💎 Crystaly — Jak to funguje</div>
      <div class="sup-two-col">
        <div class="sup-col">
          <div class="sup-col-title">📥 Zdroje crystalů (zdarma)</div>
          <div class="sup-earn-list">${sourceRows}</div>
          <div class="sup-earn-note">
            💡 Aktivní hráč vydělá <strong>300–600 💎 měsíčně</strong> bez jakékoliv platby.
          </div>
        </div>
        <div class="sup-col">
          <div class="sup-col-title">🛒 Ceny v Crystal shopu</div>
          <div class="sup-shop-list">${shopRows}</div>
          <div class="sup-earn-note">
            ⚠️ Žádná z těchto položek nedává <strong>bojovou výhodu</strong>.
            Pouze vzhled a QoL.
          </div>
        </div>
      </div>
    </div>`;
}

function _typeLabel(type) {
  const m = { consumable: 'Spotřební', name_color: 'Kosmetika', portrait_frame: 'Kosmetika' };
  return m[type] || type;
}

function _renderDropRates(dropRates) {
  if (!dropRates?.length) return '';

  const DIFF_COLOR = { easy: '#4caf50', normal: '#2196f3', hard: '#ff9800', boss: '#e91e63' };
  const RARITY_COLOR = {
    'Běžný': '#aaa', 'Neobvyklý': '#4caf50', 'Vzácný': '#2196f3',
    'Epický': '#9c27b0', 'Legendární': '#ff9800',
  };

  const tables = dropRates.map(dr => {
    const color = DIFF_COLOR[dr.difficulty] || '#888';
    const rarRows = dr.rarities.map(r => `
      <div class="sup-rar-row">
        <span class="sup-rar-dot" style="background:${RARITY_COLOR[r.label] || '#888'}"></span>
        <span class="sup-rar-label">${r.label}</span>
        <span class="sup-rar-bar-wrap">
          <span class="sup-rar-bar" style="width:${r.pct}%;background:${RARITY_COLOR[r.label] || '#888'}"></span>
        </span>
        <span class="sup-rar-pct">${r.pct}%</span>
      </div>`).join('');

    return `
      <div class="sup-drop-card">
        <div class="sup-drop-hdr" style="border-left-color:${color}">
          <span class="sup-drop-label" style="color:${color}">${dr.label}</span>
          <span class="sup-drop-chance">Drop šance: <strong>${dr.drop_chance}%</strong></span>
        </div>
        <div class="sup-drop-note">Při dropu — distribuce rarit:</div>
        <div class="sup-rar-list">${rarRows}</div>
      </div>`;
  }).join('');

  return `
    <div class="sup-section">
      <div class="sup-section-hdr">🎲 Skutečné šance — Loot drop rates</div>
      <div class="sup-drop-note-top">
        Tyto hodnoty jsou přesná kopie konstant v herním kódu (<code>game/loot.py</code>).
        Šance na drop závisí na obtížnosti questu. Distribuce rarit se uplatní pouze při úspěšném dropu.
      </div>
      <div class="sup-drop-grid">${tables}</div>
    </div>`;
}

function _renderMechanics(d) {
  const mechs = [
    { label: 'Spuštění ability v boji',  value: `${d.ability_trigger_prob}% šance za kolo`, note: 'Standardní ability (T1/subclass)' },
    { label: 'T2 ability cooldown',       value: `každé ${d.t2_cooldown_rounds}. kolo`,       note: 'Tier 2 aktivní schopnosti' },
    { label: 'Denní limit arena goldu',   value: `${d.arena_daily_gold_cap} G / den`,          note: 'Chrání ekonomiku před neomezeným farmením' },
    { label: 'ELO za výhru',             value: `+${d.elo_win} ELO`,                          note: 'Arena rating systém' },
    { label: 'ELO za prohru',            value: `−${d.elo_loss} ELO`,                         note: 'Asymetrický (win > loss)' },
    { label: 'Stat soft cap zóny',       value: '0–50 / 51–150 / 151+',                       note: '100% / 70% / 30% efektivita — zamezuje hyperinflaci' },
  ];

  const rows = mechs.map(m => `
    <div class="sup-mech-row">
      <div class="sup-mech-label">${m.label}</div>
      <div class="sup-mech-val">${m.value}</div>
      <div class="sup-mech-note">${m.note}</div>
    </div>`).join('');

  return `
    <div class="sup-section">
      <div class="sup-section-hdr">⚙️ Herní mechaniky — Přehled</div>
      <div class="sup-mech-grid">${rows}</div>
    </div>`;
}
