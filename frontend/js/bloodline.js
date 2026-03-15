// bloodline.js — Krevní linie meta-progrese

async function loadBloodline() {
  const root = document.getElementById('bloodline-root');
  if (!root) return;

  try {
    const data = await api('GET', '/bloodline/status');
    root.innerHTML = renderBloodlinePage(data);
  } catch(e) {
    root.innerHTML = `<div style="color:var(--clr-muted);text-align:center;padding:40px">Načítání selhalo.</div>`;
  }
}

function renderBloodlinePage(data) {
  const pct = data.xp_needed
    ? Math.min(100, Math.round((data.xp_in_level / data.xp_needed) * 100))
    : 100;

  const unlocksHtml = data.unlocks.length
    ? data.unlocks.map(u => `
        <div class="bl-unlock">
          <span class="bl-unlock-icon">${unlockIcon(u.type)}</span>
          <span class="bl-unlock-desc">${u.description}</span>
        </div>`).join('')
    : `<div style="color:var(--clr-muted);font-style:italic">Žádné unlocky zatím.</div>`;

  const fallenHtml = data.fallen_heroes.length
    ? data.fallen_heroes.map(h => `
        <div class="bl-fallen-entry">
          <span class="bl-fallen-name">${h.name}</span>
          <span class="bl-fallen-meta">Lv.${h.level} ${h.cls} · ${h.days_survived} dní</span>
          <span class="bl-fallen-death">☠ ${h.killed_by || '?'}</span>
        </div>`).join('')
    : `<div style="color:var(--clr-muted);font-style:italic;padding:12px 0">Žádní padlí hrdinové.</div>`;

  const memoriesHtml = data.ancestor_memories?.length
    ? `<div class="bl-section">
        <div class="bl-section-title">🔮 Paměti předků</div>
        ${data.ancestor_memories.map(m => `<div class="bl-unlock"><span class="bl-unlock-icon">🔮</span><span class="bl-unlock-desc">${m.description}</span></div>`).join('')}
       </div>`
    : '';

  return `
    <div class="bl-header">
      <div class="bl-level-badge">
        <span class="bl-level-num">${data.level}</span>
        <span class="bl-level-label">BLOODLINE</span>
      </div>
      <div class="bl-xp-wrap">
        <div class="bl-xp-bar-bg">
          <div class="bl-xp-bar-fill" style="width:${pct}%"></div>
        </div>
        <div class="bl-xp-text">
          ${data.is_max_level
            ? 'MAX LEVEL'
            : `${data.xp_in_level} / ${data.xp_needed} XP`}
        </div>
      </div>
      <div class="bl-stat">${data.fallen_count} padlých hrdinů</div>
    </div>

    <div class="bl-section">
      <div class="bl-section-title">⚔ Padlí hrdinové</div>
      <div class="bl-fallen-list">${fallenHtml}</div>
    </div>

    ${memoriesHtml}

    <div class="bl-section">
      <div class="bl-section-title">🔓 Odemčené bonusy</div>
      <div class="bl-unlocks-list">${unlocksHtml}</div>
    </div>
  `;
}

function unlockIcon(type) {
  const icons = {
    stat_bonus: '⚔',
    gold_bonus: '💰',
    cosmetic: '🎭',
    title: '👑',
    subclass_unlock_early: '⭐',
  };
  return icons[type] || '✦';
}
