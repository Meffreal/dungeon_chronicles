// hall.js — Hall of the Fallen + Living Ladder

let _hallCurrentTab = 'fallen';

async function loadHall() {
  _hallCurrentTab = 'fallen';
  switchHallTab('fallen');
}

function switchHallTab(tab) {
  _hallCurrentTab = tab;

  document.getElementById('hall-tab-fallen')?.classList.toggle('hall-tab--active', tab === 'fallen');
  document.getElementById('hall-tab-ladder')?.classList.toggle('hall-tab--active', tab === 'ladder');

  if (tab === 'fallen') loadHallFallen();
  else loadHallLadder();
}

async function loadHallFallen() {
  const root = document.getElementById('hall-root');
  if (!root) return;
  root.innerHTML = '<div style="color:var(--text2);text-align:center;padding:20px">Načítám...</div>';

  try {
    const data = await api('GET', '/hall/fallen?limit=50');
    root.innerHTML = renderFallenList(data);
  } catch (e) {
    root.innerHTML = `<div style="color:var(--clr-muted);text-align:center;padding:40px">Načítání selhalo.</div>`;
  }
}

async function loadHallLadder() {
  const root = document.getElementById('hall-root');
  if (!root) return;
  root.innerHTML = '<div style="color:var(--text2);text-align:center;padding:20px">Načítám...</div>';

  try {
    const data = await api('GET', '/hall/ladder?limit=50');
    root.innerHTML = renderLadder(data);
  } catch (e) {
    root.innerHTML = `<div style="color:var(--clr-muted);text-align:center;padding:40px">Načítání selhalo.</div>`;
  }
}

function renderFallenList(data) {
  if (!data.entries?.length) {
    return `<div style="color:var(--clr-muted);font-style:italic;text-align:center;padding:40px">
      Žádní padlí hrdinové. Buď první.
    </div>`;
  }

  return `
    <div class="hall-fallen-count">Celkem padlých: <strong>${data.total}</strong></div>
    <div class="hall-fallen-list">
      ${data.entries.map(e => `
        <div class="hall-entry">
          <div class="hall-entry-skull">☠</div>
          <div class="hall-entry-body">
            <div class="hall-entry-name">${e.hero_name}</div>
            <div class="hall-entry-meta">
              Lv.${e.hero_level} ${e.hero_cls}
              ${e.hero_faction ? `· ${e.hero_faction}` : ''}
              · přežil ${e.days_survived} dní
            </div>
            ${e.killed_by ? `<div class="hall-entry-death">Zabit: ${e.killed_by}${e.death_dungeon ? ` v ${e.death_dungeon}` : ''}</div>` : ''}
            ${e.epitaph ? `<div class="hall-entry-epitaph">"${e.epitaph}"</div>` : ''}
          </div>
          <div class="hall-entry-date">${e.died_at ? e.died_at.substring(0, 10) : ''}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderLadder(data) {
  if (!data.entries?.length) {
    return `<div style="color:var(--clr-muted);font-style:italic;text-align:center;padding:40px">
      Žádní živí hrdinové.
    </div>`;
  }

  return `
    <div class="hall-ladder-list">
      ${data.entries.map(e => `
        <div class="hall-ladder-entry ${e.rank <= 3 ? 'hall-ladder-entry--top' : ''}">
          <div class="hall-ladder-rank">${e.rank <= 3 ? ['🥇', '🥈', '🥉'][e.rank - 1] : e.rank}</div>
          <div class="hall-ladder-name">${e.name}</div>
          <div class="hall-ladder-meta">Lv.${e.level} ${e.cls}${e.faction ? ` · ${e.faction}` : ''}</div>
        </div>
      `).join('')}
    </div>
  `;
}
