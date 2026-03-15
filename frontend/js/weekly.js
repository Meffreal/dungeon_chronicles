// ── WEEKLY QUEST BOARD ────────────────────────────────────────────────────────
let weeklyData = null;

async function loadWeekly() {
  try {
    const d = await api('GET', '/weekly-quests/');
    weeklyData = d;
    renderWeekly(d);
  } catch(e) {
    const el = document.getElementById('weekly-board');
    if (el) el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-title">${esc(e.message)}</div></div>`;
  }
}

function renderWeekly(d) {
  const el = document.getElementById('weekly-board');
  if (!el) return;

  const weekEnd   = new Date(d.week_end);
  const weekEndStr = weekEnd.toLocaleDateString('cs', { weekday:'short', day:'numeric', month:'long' });

  const GOAL_LABELS = {
    kills:    'zabití',
    quests:   'questů',
    arena:    'výher',
    dungeons: 'dungeonů',
  };

  el.innerHTML = `
    <div class="weekly-header-bar">
      <div style="font-family:'Cinzel',serif;font-size:0.62rem;letter-spacing:2px;text-transform:uppercase;color:var(--text2)">
        Týdenní nástěnka questů
      </div>
      <div style="font-size:0.7rem;color:var(--text3)">Reset: ${weekEndStr}</div>
    </div>
    <div class="weekly-grid">
      ${d.quests.map(wq => {
        const barColor = wq.is_completed
          ? 'var(--green)'
          : wq.progress_pct >= 75
            ? 'var(--gold2)'
            : 'var(--blue)';
        return `
          <div class="wq-card ${wq.is_completed ? 'wq-done' : ''} ${wq.claimed ? 'wq-claimed' : ''}">
            <div class="wq-emoji">${wq.emoji}</div>
            <div class="wq-body">
              <div class="wq-label">${esc(wq.label)}</div>
              <div class="wq-desc">${esc(wq.desc)}</div>
              <div class="wq-progress-bar">
                <div class="wq-progress-fill" style="width:${wq.progress_pct}%;background:${barColor}"></div>
              </div>
              <div class="wq-progress-text">
                ${wq.progress.toLocaleString('cs')} / ${wq.goal_target.toLocaleString('cs')} ${GOAL_LABELS[wq.goal_type] || ''}
                <span style="color:var(--text3);margin-left:4px">(${wq.progress_pct}%)</span>
              </div>
            </div>
            <div class="wq-reward-col">
              <div class="wq-reward">+${wq.reward_xp} XP</div>
              <div class="wq-reward" style="color:var(--gold2)">+${wq.reward_gold.toLocaleString('cs')} G</div>
              ${wq.can_claim
                ? `<button class="btn btn-gold btn-sm wq-claim-btn" onclick="claimWeeklyQuest(${wq.slot})">Vybrat!</button>`
                : wq.claimed
                  ? `<div class="wq-claimed-badge">✅</div>`
                  : ''
              }
            </div>
          </div>`;
      }).join('')}
    </div>`;
}

async function claimWeeklyQuest(slot) {
  try {
    const d = await api('POST', `/weekly-quests/claim/${slot}`);
    toast(d.message, 's', 4000);
    addAct(`📋 Weekly quest splněn! +${d.xp_gained} XP +${d.gold_gained} G`);
    if (d.leveled_up?.length) {
      d.leveled_up.forEach(lv => toast(`🆙 Level up! Jsi nyní level ${lv}!`, 's', 5000));
    }
    updateUI(d.character);
    await loadWeekly();
  } catch(e) { toast(e.message, 'e'); }
}

// Globální helper — voláno z quest.js/arena.js po quest collectu/arenové výhře
function notifyWeeklyCompleted(list) {
  if (!list?.length) return;
  list.forEach(wq => {
    toast(`📋 Weekly quest splněn: <strong>${esc(wq.label)}</strong>!<br><small>+${wq.reward_xp} XP, +${wq.reward_gold} G — přijď si vybrat odměnu.</small>`, 's', 7000);
    addAct(`📋 Weekly splněn: ${wq.emoji} ${wq.label}`);
  });
  // Pokud je weekly stránka otevřená, refresh
  if (document.getElementById('page-weekly')?.classList.contains('active')) {
    loadWeekly();
  }
}
