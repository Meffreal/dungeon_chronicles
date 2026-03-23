// ── VEŘEJNÉ PROFILY HRÁČŮ ─────────────────────────────────────────────────────

const _PROFILE_CLS_NAMES  = { warrior: 'Válečník', mage: 'Mág', ranger: 'Střelec' };
const _PROFILE_CLS_EMOJIS = { warrior: '⚔', mage: '🔮', ranger: '🏹' };
const _PROFILE_FACTION_NAMES = {
  rad_popele:         'Řád Popele',
  pakt_stinu:         'Pakt Stínů',
  kongregace_prazdna: 'Kongregace Prázdna',
};

async function showPlayerProfile(name) {
  const modal   = document.getElementById('modal-profile');
  const content = document.getElementById('profile-modal-content');
  if (!modal || !content) return;

  content.innerHTML = `<div class="profile-loading">⏳ Načítám profil ${esc(name)}…</div>`;
  modal.classList.add('open');

  try {
    const data = await api('GET', `/character/profile/${encodeURIComponent(name)}`);
    _renderProfileModal(data);
  } catch (e) {
    content.innerHTML = `<div class="profile-error">❌ ${esc(e.message || 'Profil nenalezen.')}</div>`;
  }
}

function closeProfileModal() {
  const modal = document.getElementById('modal-profile');
  if (modal) modal.classList.remove('open');
}

// ── Renderování ────────────────────────────────────────────────────────────────

function _renderProfileModal(data) {
  const content = document.getElementById('profile-modal-content');
  if (!content) return;

  const isMe     = typeof char !== 'undefined' && char && char.name === data.name;
  const cls      = data.cls || 'warrior';
  const clsName  = _PROFILE_CLS_NAMES[cls]  || cls;
  const clsEmoji = _PROFILE_CLS_EMOJIS[cls] || '⚔';
  const factionName = _PROFILE_FACTION_NAMES[data.faction] || (data.faction ? data.faction : '—');

  // Avatar
  let avatarHtml = `<span style="font-size:2.5rem">${clsEmoji}</span>`;
  if (data.appearance && typeof buildAvatarUrl === 'function') {
    const url = buildAvatarUrl(data.appearance, data.name);
    avatarHtml = `<img src="${url}" alt="" style="width:72px;height:72px;border-radius:50%;object-fit:cover;">`;
  }

  // Portrait frame wrapper
  const frameKey   = data.portrait_frame || '';
  const frameClass = frameKey ? `portrait portrait-frame pf-${frameKey.replace(/^season-/, 's-')}` : 'portrait';

  // Badges
  const prestigeBadge = data.prestige_level > 0
    ? `<span class="profile-badge profile-prestige-badge">✨ Prestige ${data.prestige_level}</span>` : '';
  const subclassBadge = data.subclass
    ? `<span class="profile-badge profile-sub-badge">${data.subclass.emoji} ${esc(data.subclass.name)}</span>` : '';
  const t2Badge = data.talent_t2
    ? `<span class="profile-badge profile-t2-badge">⚡ ${esc(data.talent_t2.name)}</span>` : '';
  const titleHtml = data.current_title
    ? `<div class="profile-title">"${esc(data.current_title)}"</div>` : '';

  // Arena history
  const histHtml = data.last_matches && data.last_matches.length > 0
    ? data.last_matches.map(m => {
        const won      = m.won;
        const opponent = (m.attacker === data.name) ? m.defender : m.attacker;
        const eloChg   = m.elo_change;
        return `<div class="profile-match-row">
          <span class="profile-match-result ${won ? 'win' : 'loss'}">${won ? '🏆' : '💀'}</span>
          <span class="profile-match-opp" onclick="showPlayerProfile('${opponent}')">${esc(opponent)}</span>
          <span class="profile-match-elo ${eloChg >= 0 ? 'pos' : 'neg'}">${eloChg >= 0 ? '+' : ''}${eloChg}</span>
        </div>`;
      }).join('')
    : `<div style="color:var(--text3);font-style:italic;font-size:.75rem;padding:4px 0">Žádné zápasy.</div>`;

  // Compare section
  const compareHtml = !isMe ? _buildCompareSection(data) : '';

  content.innerHTML = `
    <div class="profile-header">
      <div class="${frameClass}" style="width:80px;height:80px;flex-shrink:0;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:50%;">
        ${avatarHtml}
      </div>
      <div class="profile-info">
        <div class="profile-name">
          ${esc(data.name)}
          ${isMe ? '<span class="profile-me-badge">Ty</span>' : ''}
        </div>
        ${titleHtml}
        <div class="profile-meta">${clsEmoji} ${clsName} · Lv. ${data.level}</div>
        <div class="profile-badges">${prestigeBadge}${subclassBadge}${t2Badge}</div>
        <div class="profile-faction-line">${factionName}</div>
      </div>
    </div>

    <div class="profile-section-grid">
      <!-- ARÉNA -->
      <div class="profile-section">
        <div class="profile-section-title">⚔ Aréna</div>
        <div class="profile-arena-stats">
          <div class="profile-arena-stat">
            <div class="profile-stat-val c-purple">${data.arena.rank}</div>
            <div class="profile-stat-lbl">ELO</div>
          </div>
          <div class="profile-arena-stat">
            <div class="profile-stat-val">
              <span class="c-green">${data.arena.wins}W</span>
              <span style="color:var(--accent2);font-size:1rem">${data.arena.losses}L</span>
            </div>
            <div class="profile-stat-lbl">Zápasy</div>
          </div>
          <div class="profile-arena-stat">
            <div class="profile-stat-val c-gold">${data.arena.win_rate}%</div>
            <div class="profile-stat-lbl">Win Rate</div>
          </div>
        </div>
        <div class="profile-subsection-title">Poslední zápasy</div>
        <div class="profile-match-list">${histHtml}</div>
      </div>

      <!-- STATISTIKY -->
      <div class="profile-section">
        <div class="profile-section-title">📊 Bojové statistiky</div>
        <div class="profile-combat-stats">
          <div class="profile-combat-row"><span>⚔ ATK</span><span class="c-red">${data.combat.atk}</span></div>
          <div class="profile-combat-row"><span>🛡 DEF</span><span class="c-blue">${data.combat.def}</span></div>
          <div class="profile-combat-row"><span>💨 SPD</span><span class="c-green">${data.combat.spd}</span></div>
          <div class="profile-combat-row"><span>❤ HP</span><span class="c-pink">${data.combat.hp}</span></div>
          <div class="profile-combat-row"><span>🔵 MP</span><span class="c-cyan">${data.combat.mp}</span></div>
        </div>
        <div class="profile-ach-chip">🏅 ${data.achievement_count} achievementů</div>
      </div>
    </div>

    ${compareHtml}
  `;
}

// ── Compare feature ────────────────────────────────────────────────────────────

function _buildCompareSection(data) {
  if (typeof char === 'undefined' || !char) return '';

  const myCs = _computeCombatStats(char);
  const th = data.combat || {};

  const myAtk = myCs.atk;
  const myDef = myCs.def;
  const mySpd = myCs.spd;
  const myHp  = myCs.hp;
  const myMp  = myCs.mp;

  const myArena = char.arena || {};
  const total   = (myArena.wins || 0) + (myArena.losses || 0);
  const myWr    = total > 0 ? Math.round((myArena.wins || 0) / total * 100) : 0;

  const row = (label, myVal, theirVal) => {
    const diff = myVal - theirVal;
    const myC  = diff > 0 ? '#60d080' : diff < 0 ? '#f06878' : 'var(--text2)';
    const thC  = diff < 0 ? '#60d080' : diff > 0 ? '#f06878' : 'var(--text2)';
    return `<div class="compare-row">
      <span style="color:${myC};font-weight:${diff !== 0 ? 700 : 400}">${myVal}</span>
      <span class="compare-key">${label}</span>
      <span style="color:${thC};font-weight:${diff !== 0 ? 700 : 400}">${theirVal}</span>
    </div>`;
  };

  return `
    <div class="profile-section profile-compare-section">
      <div class="profile-section-title">⚖ Porovnání buildů</div>
      <div class="compare-header">
        <span class="compare-me">${esc(char.name)}</span>
        <span></span>
        <span class="compare-them">${esc(data.name)}</span>
      </div>
      <div class="compare-table">
        ${row('⚔ ATK', myAtk,            th.atk  || 0)}
        ${row('🛡 DEF', myDef,            th.def  || 0)}
        ${row('💨 SPD', mySpd,            th.spd  || 0)}
        ${row('❤ HP',  myHp,             th.hp   || 0)}
        ${row('🔵 MP',  myMp,             th.mp   || 0)}
        ${row('🏆 ELO', myArena.rank || 1000, data.arena.rank || 1000)}
        ${row('📈 Win%', myWr,             data.arena.win_rate || 0)}
      </div>
    </div>`;
}
