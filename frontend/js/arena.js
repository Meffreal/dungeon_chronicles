// ── ARÉNA ─────────────────────────────────────────────────────────────────
let lastBattleLog          = [];
let lastArenaEvents        = null;   // structured events z unified engine (pro replay)
let lastArenaWon           = false;
let lastArenaDefName       = '';
let lastArenaPlayerHp      = 100;
let lastArenaEnemyHp       = 100;
let lastArenaEnemyAppearance = null;  // appearance soupeře pro combat replay
let attackInProgress       = false;
let _arenaOpponents        = [];      // cache opponent listu (včetně appearance)

function _replayArenaFight() {
  try {
    showCombatReplay(
      (lastArenaEvents && lastArenaEvents.length) ? lastArenaEvents : lastBattleLog,
      (typeof char !== 'undefined' && char?.name) ? char.name : 'Hráč',
      lastArenaDefName || 'Soupeř',
      lastArenaWon,
      lastArenaPlayerHp,
      lastArenaEnemyHp,
      {
        playerAppearance: (typeof char !== 'undefined') ? char?.appearance : null,
        enemyAppearance:  lastArenaEnemyAppearance,
      }
    );
  } catch(e) {
    console.error('Combat replay error:', e);
  }
}

function _arenaAvatarHtml(p, size) {
  if (p.appearance && typeof buildAvatarUrl === 'function') {
    const sz  = size === 'sm' ? 26 : 48;
    const url = buildAvatarUrl(p.appearance, p.id || 'opp');
    return `<img src="${url}" alt="" style="width:${sz}px;height:${sz}px;border-radius:50%;object-fit:cover;" loading="lazy">`;
  }
  return p.cls_emoji || '⚔';
}
let arenaCooldownTimer = null;
let arenaCooldownUntil = null;
const ARENA_COOLDOWN_TOTAL_SECS = 300;

function startArenaCooldown(untilISO) {
  if (!untilISO) return;
  arenaCooldownUntil = new Date(untilISO);
  if (arenaCooldownTimer) clearInterval(arenaCooldownTimer);
  _tickArenaCooldown();
  arenaCooldownTimer = setInterval(_tickArenaCooldown, 1000);
}

function _tickArenaCooldown() {
  const wrap = document.getElementById('arena-cooldown-wrap');
  if (!wrap) return;

  const now = new Date();
  if (!arenaCooldownUntil || now >= arenaCooldownUntil) {
    clearInterval(arenaCooldownTimer);
    arenaCooldownTimer = null;
    arenaCooldownUntil = null;
    wrap.style.display = 'none';
    document.querySelectorAll('.attack-btn').forEach(b => b.disabled = false);
    return;
  }

  const secondsLeft = Math.max(0, (arenaCooldownUntil - now) / 1000);
  const pctVal = Math.round((secondsLeft / ARENA_COOLDOWN_TOTAL_SECS) * 100);
  const mins = Math.floor(secondsLeft / 60);
  const secs = Math.floor(secondsLeft % 60);

  wrap.style.display = 'block';
  wrap.innerHTML = `
    <div class="arena-cooldown">
      <div class="arena-cd-label">
        <span>⏱ Cooldown útoku</span>
        <span class="arena-cd-time">${mins}:${String(secs).padStart(2,'0')}</span>
      </div>
      <div class="arena-cd-track">
        <div class="arena-cd-fill" style="width:${pctVal}%"></div>
      </div>
    </div>`;
  document.querySelectorAll('.attack-btn').forEach(b => b.disabled = true);
}

async function loadArena() {
  showLoading('arena-opponents');
  try {
    const [opp, hist, lb, season, myResult] = await Promise.all([
      api('GET', '/arena/opponents'),
      api('GET', '/arena/history'),
      api('GET', '/arena/season/leaderboard'),
      api('GET', '/arena/season'),
      api('GET', '/arena/season/my-result'),
    ]);
    // strategy picker schovaný — TODO: vrátit až bude vylepšen
    renderSeasonBanner(season.season, myResult);
    renderArenaStats(opp);
    renderOpponents(opp.opponents);
    renderArenaHistory(hist.matches);
    renderArenaLB(lb);
    if (opp.cooldown_until && !arenaCooldownTimer) {
      startArenaCooldown(opp.cooldown_until);
    }
    // Zkontroluj a případně zobraz Season Recap modal
    _maybeShowSeasonRecap();
  } catch(e) { toast(e.message, 'e'); }
}

const _SEASON_FRAME_LABELS = {
  'season-champion':   { label: '🏆 Grand Champion Frame', cls: '' },
  'season-challenger': { label: '🥈 Champion Frame',       cls: 'challenger' },
  'season-veteran':    { label: '🥉 Veteran Frame',        cls: 'veteran' },
};

function _seasonFrameBadgeHtml(frameKey) {
  if (!frameKey) return '';
  const info = _SEASON_FRAME_LABELS[frameKey];
  if (!info) return '';
  return `<span class="season-frame-badge ${info.cls}">${info.label}</span>`;
}

function _seasonCosmeticPreviewHtml(myResult) {
  if (!myResult || !myResult.unclaimed_cosmetics?.length) return '';
  const tags = myResult.unclaimed_cosmetics.map(c => {
    const parts = [];
    if (c.frame && _SEASON_FRAME_LABELS[c.frame]) parts.push(_SEASON_FRAME_LABELS[c.frame].label);
    if (c.title) parts.push(`Titul: "${c.title}"`);
    return parts.map(p => `<span class="season-cosmetic-tag">✨ ${esc(p)}</span>`).join('');
  }).join('');
  return `<div class="season-cosmetic-preview">${tags}</div>`;
}

function renderSeasonBanner(season, myResult) {
  const el = document.getElementById('season-banner');
  if (!el) return;

  const hasUnclaimed = myResult && myResult.unclaimed_count > 0;
  const hasCosmeticUnclaimed = myResult?.unclaimed_cosmetics?.length > 0;
  const currentFrame = myResult?.current_season_frame;

  const timeStr = season.days_remaining > 0
    ? `Zbývá ${season.days_remaining} dní`
    : season.hours_remaining > 0
      ? `Zbývá ${season.hours_remaining} hodin`
      : 'Sezóna expiruje...';

  const frameDisplay = currentFrame
    ? `<div style="margin-top:4px">${_seasonFrameBadgeHtml(currentFrame)}</div>` : '';

  const themeName = season.theme_name ? `<div class="season-theme-name">${esc(season.theme_name)}</div>` : '';
  const themeLore = season.theme_lore ? `<div class="season-theme-lore">${esc(season.theme_lore)}</div>` : '';

  el.innerHTML = `
    <div class="season-banner">
      <div>
        <div class="season-num">Sezóna ${season.number}</div>
        ${themeName}
        <div class="season-lbl">Arena PvP</div>
        ${frameDisplay}
      </div>
      <div style="flex:1">
        ${themeLore}
        <div class="season-timer">⏳ ${timeStr}</div>
        <div style="font-size:.68rem;color:var(--text3);margin-top:2px">
          ${new Date(season.start_at).toLocaleDateString('cs')} – ${new Date(season.end_at).toLocaleDateString('cs')}
        </div>
        ${_seasonCosmeticPreviewHtml(myResult)}
      </div>
      ${hasUnclaimed
        ? `<div style="text-align:right">
             <div style="font-size:.68rem;color:var(--gold2);margin-bottom:4px">💰 ${myResult.total_unclaimed_gold} G čeká</div>
             ${hasCosmeticUnclaimed ? '<div style="font-size:.62rem;color:var(--text2);margin-bottom:4px">+ kosmetické odměny!</div>' : ''}
             <button class="season-claim-btn" onclick="claimSeasonRewards()">Vybrat odměny</button>
           </div>`
        : `<div style="font-size:.68rem;color:var(--text3);font-family:'Cinzel',serif">žádné odměny<br>k vyzvednutí</div>`
      }
    </div>`;
}

async function claimSeasonRewards() {
  try {
    const d = await api('POST', '/arena/season/claim');
    toast(d.message, 's', 6000);

    let actStr = `💰 Sezónní odměna: +${d.gold_gained} G`;
    if (d.frame_applied) actStr += ` · 🖼 Frame: ${d.frame_applied}`;
    if (d.title_applied) actStr += ` · ✨ Titul: "${d.title_applied}"`;
    addAct(actStr);

    // Speciální toast pro kosmetické odměny
    if (d.frame_applied) {
      const fInfo = _SEASON_FRAME_LABELS[d.frame_applied];
      toast(`🖼 Exkluzivní frame odemčen: ${fInfo ? fInfo.label : d.frame_applied}`, 's', 7000);
    }
    if (d.title_applied) {
      toast(`✨ Titul přiřazen: "${d.title_applied}"`, 's', 6000);
    }

    updateUI(d.character);
    await loadArena();
  } catch(e) { toast(e.message, 'e'); }
}

function renderArenaStats(data) {
  const wr = data.my_wins + data.my_losses > 0
    ? Math.round(data.my_wins / (data.my_wins + data.my_losses) * 100) : 0;
  const cap   = data.arena_daily_cap  || 500;
  const today = data.arena_gold_today || 0;
  const pct   = Math.min(100, Math.round(today / cap * 100));
  const capColor = pct >= 100 ? '#f06878' : pct >= 80 ? '#c89010' : 'var(--gold2)';
  document.getElementById('arena-my-stats').innerHTML = `
    <div class="arena-stat-card">
      <div class="arena-stat-val c-purple">${data.my_rank}</div>
      <div class="arena-stat-lbl">ELO Rating</div>
    </div>
    <div class="arena-stat-card">
      <div class="arena-stat-val c-green">${data.my_wins}W <span style="color:var(--accent2);font-size:1.2rem">${data.my_losses}L</span></div>
      <div class="arena-stat-lbl">Výsledky</div>
    </div>
    <div class="arena-stat-card">
      <div class="arena-stat-val c-gold">${wr}%</div>
      <div class="arena-stat-lbl">Win Rate</div>
    </div>
    <div class="arena-stat-card arena-gold-cap-card" style="grid-column:1/-1">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:.72rem;color:var(--text3)">💰 Denní limit arény</span>
        <span style="font-size:.8rem;color:${capColor};font-weight:700">${today} / ${cap} G</span>
      </div>
      <div class="arena-cap-track">
        <div class="arena-cap-fill" style="width:${pct}%;background:${capColor}"></div>
      </div>
      ${pct >= 100 ? '<div style="font-size:.68rem;color:#f06878;margin-top:3px">⛔ Denní limit dosažen — zítra se resetuje</div>' : ''}
    </div>`;
}

function renderOpponents(opponents) {
  _arenaOpponents = opponents;
  const el = document.getElementById('arena-opponents');
  if (!opponents.length) {
    el.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚔️</div>
        <div class="empty-state-title">Zatím nikdo k dispozici.</div>
        <div class="empty-state-hint">Zkus za chvíli.</div>
      </div>`;
    return;
  }
  el.innerHTML = opponents.map(o => {
    const wc = Math.round(o.win_chance * 100);
    const wcc = wc >= 60 ? '#30a848' : wc >= 40 ? '#c89010' : '#b82030';
    const eloDiff = o.arena_rank - (char?.arena?.rank || 1000);
    const eloDiffStr = eloDiff > 0 ? `+${eloDiff}` : `${eloDiff}`;
    return `
      <div class="opponent-card">
        <div class="opp-avatar">${_arenaAvatarHtml(o)}</div>
        <div>
          <div class="opp-name player-name-link" onclick="showPlayerProfile('${o.name}')">${esc(o.name)}</div>
          <div class="opp-meta">Lv.${o.level} ${o.cls_name} · ${o.wins}W/${o.losses}L</div>
          <div class="opp-elo">ELO: ${o.arena_rank} <span style="color:${eloDiff>=0?'#e06060':'#60d080'};font-size:.65rem">(${eloDiffStr})</span></div>
          <div class="opp-wc-bar"><div class="opp-wc-fill" style="width:${wc}%;background:${wcc}"></div></div>
          <div style="font-size:.65rem;color:${wcc};margin-top:2px">Šance na výhru: ${wc}%</div>
        </div>
        <button class="attack-btn" id="atk-${o.id}" onclick="doAttack(${o.id},'${esc(o.name)}')">
          ⚔ Útok
        </button>
      </div>`;
  }).join('');
}

async function doAttack(defenderId, defenderName) {
  if (attackInProgress) return;
  attackInProgress = true;
  const _oppData = _arenaOpponents.find(o => o.id === defenderId);
  lastArenaEnemyAppearance = _oppData?.appearance || null;

  document.querySelectorAll('.attack-btn').forEach(b => b.disabled = true);
  toast(`⚔ Útočíš na ${esc(defenderName)}...`, 'i', 2000);

  try {
    const d = await api('POST', `/arena/attack/${defenderId}`, {});
    const won = d.attacker_won;
    lastBattleLog     = d.battle_log   || [];
    lastArenaEvents   = d.events       || null;
    lastArenaWon      = won;
    lastArenaDefName  = defenderName;
    lastArenaPlayerHp = d.character?.combat?.hp_max || 100;
    lastArenaEnemyHp  = d.enemy_hp_max || 100;

    const resultEl = document.getElementById('arena-result');
    resultEl.style.display = 'block';
    const arcRgb = won ? '32,168,64' : '184,32,48';
    const charName = (typeof char !== 'undefined' && char?.name) ? esc(char.name) : 'Ty';
    const charCls  = (typeof char !== 'undefined' && char?.cls)  ? esc(char.cls) : '';
    resultEl.innerHTML = `
      <div class="arena-result-card ${won ? 'win' : 'loss'}" style="--arc-rgb:${arcRgb}">
        <div class="arc-header">
          <div class="arc-outcome ${won ? 'win' : 'loss'}">${won ? '⚔ VÍTĚZSTVÍ' : '💀 PORÁŽKA'}</div>
        </div>
        <div class="arc-vs">
          <div class="arc-fighter">
            <div class="arc-fighter-name">${charName}</div>
            <div class="arc-fighter-cls">${charCls}</div>
          </div>
          <div class="arc-divider">VS</div>
          <div class="arc-fighter enemy">
            <div class="arc-fighter-name">${esc(defenderName)}</div>
            <div class="arc-fighter-cls">soupeř</div>
          </div>
        </div>
        <div class="arc-elo">
          <div class="arc-elo-delta ${d.elo_change>=0?'pos':'neg'}">${d.elo_change>=0?'+':''}${d.elo_change} ELO</div>
          <div class="arc-elo-total">Celkem: ${d.new_elo} ELO</div>
        </div>
        <div class="arc-rewards">
          ${d.gold_earned>0?`<div class="arc-reward-chip">💰 +${d.gold_earned} Gold</div>`:''}
          ${(d.xp_gained||0)>0?`<div class="arc-reward-chip">✨ +${d.xp_gained} XP</div>`:''}
          ${d.gold_cap_reached?`<div class="arc-reward-chip" style="border-color:rgba(240,100,120,.3);color:#f06878">⛔ Denní limit</div>`:''}
        </div>
        <div class="arc-actions">
          <button class="result-log-btn" onclick="toggleArenaLog()">📜 Textový log</button>
          <button class="result-log-btn" style="background:rgba(192,57,43,.1);border-color:var(--accent)" onclick="_replayArenaFight()">⚔ Přehrát znovu</button>
        </div>
      </div>
      <div id="arena-insights"></div>`;

    // Auto-spustí combat replay okamžitě
    _replayArenaFight();
    // Zobraz Combat Insights
    if (typeof showCombatInsights === 'function') {
      showCombatInsights('arena-insights', lastArenaEvents, won,
        (typeof char !== 'undefined' ? char?.name : null) || 'Hráč',
        typeof char !== 'undefined' ? char?.cls : null,
        null);
    }

    updateUI(d.character);
    if (d.leveled_up?.length) {
      const lv = d.leveled_up.at(-1);
      const sp = d.character?.stat_points || 0;
      const spHint = sp > 0 ? ` · <span style="color:var(--green2);cursor:pointer" onclick="showPage('equipment')">Přiděl ${sp} bod${sp===1?'':'y'}!</span>` : '';
      toast(`⚡ Level up! Nyní level ${lv}${spHint}`, 's', 7000);
    }
    addAct(`${won ? '🏆' : '💀'} Aréna vs ${defenderName}: ${won ? 'výhra' : 'prohra'} (${d.elo_change >= 0 ? '+' : ''}${d.elo_change} ELO, +${d.xp_gained||0} XP)`);
    toast(`${won ? '🏆 Vítězství!' : '💀 Prohra'} vs ${esc(defenderName)} · ${d.elo_change >= 0 ? '+' : ''}${d.elo_change} ELO · +${d.xp_gained||0} XP`, won ? 's' : 'e', 5000);
    showAchievementToasts(d.new_achievements);
    if (typeof notifyWeeklyCompleted === 'function') notifyWeeklyCompleted(d.weekly_completed);

    if (d.character?.arena?.cooldown_until) {
      startArenaCooldown(d.character.arena.cooldown_until);
    }

    await loadArena();
    loadNotifications();
  } catch(e) {
    toast(e.message, 'e');
  } finally {
    attackInProgress = false;
  }
}

function toggleArenaLog() {
  const wrap = document.getElementById('arena-log-wrap');
  if (wrap.style.display === 'none') {
    wrap.style.display = 'block';
    document.getElementById('arena-log').innerHTML = lastBattleLog.map(line => {
      const cls = line.includes('zvítězil') || line.includes('přežil') ? 'bwin'
                : line.includes('poražen') ? 'blose'
                : line.includes('KRITICKÝ') ? 'bcrit'
                : line.startsWith('[Kolo') || line.startsWith('─') || line.startsWith('⚔') ? 'bsep' : '';
      return `<div class="${cls}">${esc(line)}</div>`;
    }).join('');
  } else {
    wrap.style.display = 'none';
  }
}

function renderArenaHistory(matches) {
  const el = document.getElementById('arena-history');
  if (!matches.length) {
    el.innerHTML = '<div style="color:var(--text3);font-size:.75rem;font-style:italic">Zatím žádné zápasy...</div>';
    return;
  }
  el.innerHTML = matches.slice(0, 8).map(m => {
    const won = m.won;
    const opponent = char && m.attacker_id === char.id ? m.defender : m.attacker;
    const eloChange = m.elo_change;
    return `<div class="hist-row">
      <div class="hist-result">${won ? '🏆' : '💀'}</div>
      <div class="hist-name player-name-link" onclick="showPlayerProfile('${opponent}')">${esc(opponent)}</div>
      <div class="hist-elo" style="color:${eloChange >= 0 ? '#60d080' : '#f06878'}">${eloChange >= 0 ? '+' : ''}${eloChange}</div>
    </div>`;
  }).join('');
}

// Potenciální sezónní framy pro top-10 hráčů (preview před koncem sezóny)
const _RANK_FRAME_PREVIEW = {
  1: 'season-champion', 2: 'season-challenger', 3: 'season-challenger',
};
function _lbRankFrameHtml(rank) {
  const fk = _RANK_FRAME_PREVIEW[rank];
  if (!fk) return '';
  const info = _SEASON_FRAME_LABELS[fk];
  return info ? `<span title="${info.label}" style="font-size:.6rem;opacity:.7">${rank===1?'👑':rank<=3?'🎖':''}</span>` : '';
}

function renderArenaLB(lb) {
  const el = document.getElementById('arena-lb');
  const rankClass = r => r === 1 ? 'gold' : r === 2 ? 'silver' : r === 3 ? 'bronze' : '';
  const medals = {1:'🥇',2:'🥈',3:'🥉'};
  const rows = lb.slice(0, 10).map(p => {
    const isMe = char && p.name === char.name;
    return `<div class="season-lb-row" style="${isMe ? 'color:var(--gold2)' : ''}">
      <div class="season-lb-rank ${rankClass(p.rank)}">${medals[p.rank] || p.rank}</div>
      <div style="width:26px;height:26px;flex-shrink:0;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:50%;">${_arenaAvatarHtml(p, 'sm')}</div>
      <div class="player-name-link" onclick="showPlayerProfile('${p.name}')" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem">${esc(p.name)} ${_lbRankFrameHtml(p.rank)}</div>
      <div style="font-size:.66rem;color:var(--text2)">${p.winrate}%</div>
      <div class="lb-elo">${p.arena_rank}</div>
    </div>`;
  }).join('');
  el.innerHTML = rows || `
    <div class="empty-state">
      <div class="empty-state-icon">🏆</div>
      <div class="empty-state-title">Žebříček je prázdný.</div>
      <div class="empty-state-hint">Buď první!</div>
    </div>`;
}

// ── SEASON RECAP MODAL ────────────────────────────────────────────────────────

let _recapChecked = false;  // zkontrolujeme jen jednou za session

async function _maybeShowSeasonRecap() {
  if (_recapChecked) return;
  _recapChecked = true;
  try {
    const d = await api('GET', '/arena/season/recap');
    if (d.recap) showSeasonRecap(d.recap);
  } catch(e) { /* tichá chyba — recap není kritický */ }
}

function _buildEloChartSvg(eloPoints) {
  if (!eloPoints || eloPoints.length < 2) return '';
  const W = 280, H = 80, PAD = 10;
  const minElo = Math.min(...eloPoints);
  const maxElo = Math.max(...eloPoints);
  const range  = maxElo - minElo || 1;
  const n = eloPoints.length;

  const px = i => PAD + (i / (n - 1)) * (W - 2 * PAD);
  const py = v => H - PAD - ((v - minElo) / range) * (H - 2 * PAD);

  const pts = eloPoints.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ');
  const last = eloPoints[n - 1];
  const first = eloPoints[0];
  const trend = last >= first ? '#60d080' : '#f06878';

  // Fill area pod čarou
  const fillPts = `${px(0).toFixed(1)},${H - PAD} ` + pts + ` ${px(n-1).toFixed(1)},${H - PAD}`;

  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="recap-elo-chart">
    <defs>
      <linearGradient id="rcg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${trend}" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="${trend}" stop-opacity="0.03"/>
      </linearGradient>
    </defs>
    <polygon points="${fillPts}" fill="url(#rcg)"/>
    <polyline points="${pts}" fill="none" stroke="${trend}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${px(0).toFixed(1)}" cy="${py(first).toFixed(1)}" r="3" fill="${trend}" opacity="0.6"/>
    <circle cx="${px(n-1).toFixed(1)}" cy="${py(last).toFixed(1)}" r="4" fill="${trend}"/>
    <text x="${px(0).toFixed(1)}" y="${py(first).toFixed(1) - 5}" font-size="8" fill="${trend}" opacity="0.8" text-anchor="middle">${first}</text>
    <text x="${px(n-1).toFixed(1)}" y="${py(last).toFixed(1) - 5}" font-size="8" fill="${trend}" text-anchor="middle">${last}</text>
  </svg>`;
}

function _recapRankBadgeHtml(rank) {
  if (rank === 1) return `<div class="recap-rank-badge rank-1">🏆 #1</div>`;
  if (rank <= 3) return `<div class="recap-rank-badge rank-top3">🥈 #${rank}</div>`;
  if (rank <= 10) return `<div class="recap-rank-badge rank-top10">🎖 #${rank}</div>`;
  if (rank <= 25) return `<div class="recap-rank-badge rank-top25">#${rank}</div>`;
  return `<div class="recap-rank-badge">#${rank}</div>`;
}

function _recapFrameHtml(frameKey) {
  if (!frameKey) return '';
  const info = _SEASON_FRAME_LABELS[frameKey];
  return `<div class="recap-cosmetic-tag">${info ? info.label : frameKey}</div>`;
}

function showSeasonRecap(recap) {
  // Odstraň starý modal pokud existuje
  document.getElementById('season-recap-overlay')?.remove();

  const eloChange = recap.final_elo - recap.start_elo;
  const eloSign   = eloChange >= 0 ? '+' : '';
  const eloColor  = eloChange >= 0 ? '#60d080' : '#f06878';
  const wr = recap.total_matches > 0
    ? Math.round(recap.wins / recap.total_matches * 100) : 0;

  const chart = _buildEloChartSvg(recap.elo_points);

  const cosmeticHtml = [
    recap.reward_frame ? _recapFrameHtml(recap.reward_frame) : '',
    recap.reward_title ? `<div class="recap-cosmetic-tag">✨ Titul: "${esc(recap.reward_title)}"</div>` : '',
    recap.reward_gold  ? `<div class="recap-cosmetic-tag">💰 ${recap.reward_gold} G</div>` : '',
  ].filter(Boolean).join('');

  const topOppHtml = recap.top_opponent
    ? `<div class="recap-stat-item">
        <span class="recap-stat-lbl">Nejčastější soupeř</span>
        <span class="recap-stat-val">${esc(recap.top_opponent)} (${recap.top_opponent_count}×)</span>
       </div>` : '';

  const overlay = document.createElement('div');
  overlay.id = 'season-recap-overlay';
  overlay.className = 'season-recap-overlay';
  overlay.innerHTML = `
    <div class="season-recap-modal" role="dialog" aria-modal="true">
      <div class="recap-header">
        <div class="recap-title-row">
          <span class="recap-eyebrow">Sezóna ${recap.season_number} skončila</span>
          ${recap.season_theme ? `<span class="recap-theme-badge">${esc(recap.season_theme)}</span>` : ''}
        </div>
        <div class="recap-headline">Tvůj sezónní přehled</div>
      </div>

      <div class="recap-body">
        <div class="recap-rank-section">
          ${_recapRankBadgeHtml(recap.final_rank)}
          <div class="recap-elo-delta" style="color:${eloColor}">
            ELO: ${eloSign}${eloChange} → ${recap.final_elo}
          </div>
        </div>

        ${chart ? `<div class="recap-chart-wrap">
          <div class="recap-chart-lbl">ELO vývoj</div>
          ${chart}
        </div>` : ''}

        <div class="recap-stats-grid">
          <div class="recap-stat-item">
            <span class="recap-stat-lbl">Výsledky</span>
            <span class="recap-stat-val"><span style="color:#60d080">${recap.wins}W</span> / <span style="color:#f06878">${recap.losses}L</span></span>
          </div>
          <div class="recap-stat-item">
            <span class="recap-stat-lbl">Win rate</span>
            <span class="recap-stat-val" style="color:${wr>=50?'#60d080':'#c89010'}">${wr}%</span>
          </div>
          ${topOppHtml}
        </div>

        ${cosmeticHtml ? `<div class="recap-cosmetics-row">
          <div class="recap-cosmetics-lbl">Odměny</div>
          <div class="recap-cosmetics-tags">${cosmeticHtml}</div>
        </div>` : ''}
      </div>

      <div class="recap-footer">
        <button class="recap-close-btn" onclick="dismissSeasonRecap()">Pokračovat do nové sezóny ⚔</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  // Animace vplouvaní
  requestAnimationFrame(() => {
    requestAnimationFrame(() => overlay.classList.add('visible'));
  });
}

async function dismissSeasonRecap() {
  const overlay = document.getElementById('season-recap-overlay');
  if (overlay) {
    overlay.classList.remove('visible');
    setTimeout(() => overlay.remove(), 350);
  }
  try { await api('POST', '/arena/season/recap/dismiss'); } catch(e) { /* tichá chyba */ }
}
