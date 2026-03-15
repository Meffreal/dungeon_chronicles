// ── ACHIEVEMENTY ──────────────────────────────────────────────────────────
async function loadAchievements() {
  try {
    const d = await api('GET', '/achievements/');
    renderAchievements(d);
  } catch(e) { toast(e.message, 'e'); }
}

function renderAchievements(d) {
  const el = document.getElementById('ach-content');
  const pctVal = Math.round(d.unlocked_count / d.total_count * 100);

  const CAT_ORDER = ['level','quest','arena','wealth','market','guild','special'];

  let html = `
    <div class="ach-points-bar">
      <div>
        <div class="ach-points-num">${d.total_points}</div>
        <div class="ach-points-lbl">Achievement bodů</div>
      </div>
      <div style="flex:1">
        <div style="display:flex;justify-content:space-between;font-size:.65rem;color:var(--text2);font-family:'Cinzel',serif;margin-bottom:5px">
          <span>${d.unlocked_count} / ${d.total_count} odemčeno</span>
          <span>${pctVal}%</span>
        </div>
        <div class="ach-progress-track">
          <div class="ach-progress-fill" style="width:${pctVal}%"></div>
        </div>
      </div>
      <div style="font-size:0.65rem;color:var(--text2);text-align:right;font-family:'Cinzel',serif">
        <div style="color:var(--text3)">Max bodů</div>
        <div style="color:var(--gold)">${d.max_points}</div>
      </div>
    </div>`;

  // ── Achievement chains ───────────────────────────────────────────────────
  if (d.chains && d.chains.length) {
    const completedCount = d.chains.filter(c => c.completed).length;
    html += `
    <div class="ach-chains-section">
      <div class="ach-chains-header">
        <span>Cesty dobrodruha</span>
        <span class="ach-cat-count">${completedCount}/${d.chains.length} dokončeno</span>
      </div>
      ${d.chains.map(c => _renderChain(c)).join('')}
    </div>`;
  }

  for (const cat of CAT_ORDER) {
    const items = d.categories[cat];
    if (!items) continue;
    const catName = d.category_names[cat] || cat;
    const unlockedInCat = items.filter(a => a.unlocked).length;

    html += `<div class="ach-category">
      <div class="ach-cat-title">
        ${catName}
        <span class="ach-cat-count">${unlockedInCat}/${items.length}</span>
      </div>
      <div class="ach-grid">
        ${items.map(a => {
          const dt = a.unlocked_at ? new Date(a.unlocked_at) : null;
          const dateStr = dt
            ? `${dt.toLocaleDateString('cs')} ${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`
            : null;
          return `<div class="ach-card ${a.unlocked ? 'unlocked' : 'locked'}">
            <div class="ach-icon">${a.icon}</div>
            <div style="flex:1;min-width:0">
              <div class="ach-name">${esc(a.name)}</div>
              <div class="ach-desc">${esc(a.desc)}</div>
              ${a.unlocked && a.title ? `<div class="ach-title-badge">🎖 [${esc(a.title)}]</div>` : ''}
              ${dateStr ? `<div class="ach-date">${dateStr}</div>` : ''}
            </div>
            <div class="ach-pts">+${a.points}</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

  el.innerHTML = html;
}

function _renderChain(c) {
  const pct = Math.round(c.steps_done / c.steps_total * 100);
  const isCompleted = c.completed;

  const stepsHtml = c.steps.map((step, idx) => {
    const isLast = idx === c.steps.length - 1;
    return `
      <div class="ach-chain-step-wrap">
        <div class="ach-chain-node ${step.unlocked ? 'unlocked' : 'locked'}" title="${esc(step.name)}">
          <span class="ach-chain-node-icon">${step.icon}</span>
        </div>
        <div class="ach-chain-node-name">${esc(step.name)}</div>
        ${!isLast ? '<div class="ach-chain-connector"></div>' : ''}
      </div>`;
  }).join('');

  return `
  <div class="ach-chain ${isCompleted ? 'completed' : ''}">
    <div class="ach-chain-top">
      <div class="ach-chain-title-row">
        <span class="ach-chain-icon">${c.icon}</span>
        <span class="ach-chain-name">${esc(c.name)}</span>
        ${isCompleted ? '<span class="ach-chain-done-badge">✓ Dokončeno</span>' : ''}
      </div>
      <div class="ach-chain-desc">${esc(c.desc)}</div>
      <div class="ach-chain-reward">
        <span class="ach-chain-reward-pill crystal">💎 ${c.reward_crystals} krystalů</span>
        <span class="ach-chain-reward-pill title">🎖 [${esc(c.reward_title)}]</span>
      </div>
    </div>
    <div class="ach-chain-track">
      ${stepsHtml}
    </div>
    <div class="ach-chain-progress-wrap">
      <div class="ach-chain-progress-bar" style="width:${pct}%"></div>
    </div>
  </div>`;
}

function showAchievementToasts(achievements) {
  if (!achievements || !achievements.length) return;
  const toastsEl = document.getElementById('toasts');
  achievements.forEach((a, i) => {
    setTimeout(() => {
      const el = document.createElement('div');
      if (a.is_chain) {
        el.className = 'ach-toast ach-toast-chain';
        el.innerHTML = `
          <div class="ach-toast-icon">${a.icon}</div>
          <div>
            <div class="ach-toast-title">Chain dokončen!</div>
            <div class="ach-toast-name">${esc(a.name)}</div>
            <div class="ach-toast-pts">💎 +${a.reward_crystals} · 🎖 [${esc(a.reward_title)}]</div>
          </div>`;
      } else {
        el.className = 'ach-toast';
        el.innerHTML = `
          <div class="ach-toast-icon">${a.icon}</div>
          <div>
            <div class="ach-toast-title">Achievement odemčen!</div>
            <div class="ach-toast-name">${esc(a.name)}</div>
            <div class="ach-toast-pts">+${a.points} bodů</div>
          </div>`;
      }
      toastsEl.append(el);
      setTimeout(() => el.remove(), 6000);
    }, i * 900);
  });
}
