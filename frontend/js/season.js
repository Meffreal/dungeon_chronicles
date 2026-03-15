// ── SEASON PASS ───────────────────────────────────────────────────────────────
let seasonData = null;

async function loadSeasonPass() {
  try {
    const d = await api('GET', '/season-pass/');
    seasonData = d;
    renderSeasonPass(d);
  } catch(e) {
    const el = document.getElementById('season-content');
    if (el) el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📅</div><div class="empty-state-title">${esc(e.message)}</div></div>`;
  }
}

function renderSeasonPass(d) {
  const el = document.getElementById('season-content');
  if (!el) return;

  const s   = d.season;
  const p   = d.progress;
  const src = d.xp_sources;

  const endDate = new Date(s.end_date);
  const now     = new Date();
  const daysLeft = Math.max(0, Math.ceil((endDate - now) / 86400000));

  // Overall XP bar k dalšímu tieru
  const nextXpReq = p.next_xp_req || (p.tiers_status.at(-1)?.xp_req || 4000);
  const prevXpReq = p.reached_tier > 0
    ? (p.tiers_status.find(t => t.tier === p.reached_tier)?.xp_req || 0)
    : 0;
  const segXp     = nextXpReq - prevXpReq;
  const segProg   = p.season_xp - prevXpReq;
  const segPct    = p.reached_tier >= 10 ? 100 : Math.min(100, Math.round(segProg / Math.max(1, segXp) * 100));

  el.innerHTML = `
    <div class="sp-header">
      <div>
        <div class="sp-season-name">${esc(s.name)}</div>
        <div class="sp-season-meta">
          Zbývá <strong>${daysLeft} dní</strong> do konce sezóny
          · Tier ${p.reached_tier} / 10
        </div>
      </div>
      <div class="sp-xp-badge">${p.season_xp.toLocaleString('cs')} XP</div>
    </div>

    ${p.reached_tier < 10 ? `
    <div class="sp-progress-wrap">
      <div style="display:flex;justify-content:space-between;font-size:.68rem;color:var(--text3);margin-bottom:4px">
        <span>Tier ${p.reached_tier} → Tier ${p.reached_tier + 1}</span>
        <span>${p.season_xp.toLocaleString('cs')} / ${nextXpReq.toLocaleString('cs')} XP</span>
      </div>
      <div class="sp-progress-bar">
        <div class="sp-progress-fill" style="width:${segPct}%"></div>
      </div>
    </div>` : `<div class="sp-max-notice">🌟 Maximální tier dosažen! Gratulujeme!</div>`}

    <div class="sp-xp-sources">
      <div class="sp-sources-title">Jak získávat Season XP</div>
      <div class="sp-sources-grid">
        <div class="sp-source"><span>⚔ Quest</span><span>+${src.quest} XP</span></div>
        <div class="sp-source"><span>🏟 Arénní výhra</span><span>+${src.arena_win} XP</span></div>
        <div class="sp-source"><span>🏰 Dungeon stage</span><span>+${src.dungeon_stage} XP</span></div>
        <div class="sp-source"><span>🏰 Dungeon dokončen</span><span>+${src.dungeon_complete} XP</span></div>
        <div class="sp-source"><span>📋 Weekly quest</span><span>+${src.weekly_claim} XP</span></div>
      </div>
    </div>

    <div class="sp-tiers-title">Rewards Track</div>
    <div class="sp-tiers">
      ${p.tiers_status.map(t => `
        <div class="sp-tier ${t.reached ? 'sp-tier-reached' : ''} ${t.claimed ? 'sp-tier-claimed' : ''}">
          <div class="sp-tier-num">Tier ${t.tier}</div>
          <div class="sp-tier-emoji">${t.emoji}</div>
          <div class="sp-tier-label">${esc(t.label)}</div>
          <div class="sp-tier-xp">${t.xp_req.toLocaleString('cs')} XP</div>
          ${t.can_claim
            ? `<button class="btn btn-gold btn-sm sp-claim-btn" onclick="claimSeasonTier(${t.tier})">Vybrat!</button>`
            : t.claimed
              ? `<div class="sp-claimed-check">✅</div>`
              : `<div class="sp-tier-locked">🔒</div>`
          }
        </div>`).join('')}
    </div>`;
}

async function claimSeasonTier(tier) {
  try {
    const d = await api('POST', `/season-pass/claim/${tier}`);
    toast(d.message, 's', 5000);
    addAct(`🏅 Season Pass Tier ${tier} — ${d.reward_title || ''}${d.reward_gold ? '+' + d.reward_gold + ' G' : ''}`);
    if (d.reward_title) {
      toast(`👑 Nový titul: <strong>${esc(d.reward_title)}</strong>`, 's', 6000);
    }
    updateUI(d.character);
    await loadSeasonPass();
  } catch(e) { toast(e.message, 'e'); }
}
