// ── ATTUNEMENT ────────────────────────────────────────────────────────────

async function loadAttunement() {
  const el = document.getElementById('att-content');
  try {
    const data = await api('GET', '/attunement/progress');
    renderAttunement(data);
  } catch(e) {
    toast(e.message, 'e');
    if (el) el.innerHTML = `<div style="color:var(--accent2);text-align:center;padding:30px;font-size:0.85rem">⚠ Nepodařilo se načíst attunement: ${esc(e.message)}</div>`;
  }
}

function renderAttunement(data) {
  const el = document.getElementById('att-content');
  if (!data?.chains?.length) {
    el.innerHTML = '<div style="color:var(--text2);font-style:italic;text-align:center;padding:40px">Žádné attunement série.</div>';
    return;
  }

  el.innerHTML = `
    <div style="color:var(--text2);font-size:0.82rem;margin-bottom:18px;line-height:1.6;padding:11px 14px;background:var(--panel);border:1px solid var(--border);border-radius:5px;border-left:3px solid var(--gold2)">
      🔑 <strong style="color:var(--gold2)">Attunement</strong> jsou vstupenky do speciálních dungeonů.
      Každý dungeon vyžaduje dokončení série pěti questů. Questy musíš plnit <em>postupně</em> — každý splněný krok odemkne další.
    </div>
    <div class="att-chains">
      ${data.chains.map(renderChain).join('')}
    </div>`;
}

function renderChain(chain) {
  const pct     = Math.round((chain.completed_steps / chain.total_steps) * 100);
  const unlocked = chain.unlocked;
  const colorHex = chain.color;

  const stepsHtml = chain.steps.map((step, i) => {
    const prev   = i > 0 ? chain.steps[i - 1] : null;
    const locked = !step.done && prev && !prev.done;
    const isCurrent = !step.done && !locked;
    const diffCls = { easy:'de', normal:'dn', hard:'dh', boss:'db' }[step.difficulty] || 'dn';

    return `<div class="att-step ${step.done ? 'att-step-done' : locked ? 'att-step-locked' : 'att-step-current'}">
      <div class="att-step-num">${step.done ? '✓' : locked ? '🔒' : step.step}</div>
      <div class="att-step-icon">${step.done ? '✅' : step.icon}</div>
      <div class="att-step-body">
        <div class="att-step-name">${esc(step.name)}</div>
        <div class="att-step-meta">
          <span class="dbadge ${diffCls}">${step.difficulty}</span>
          <span>⏱ ${step.duration}m</span>
          <span>Lv.${step.min_level}+</span>
        </div>
      </div>
      ${isCurrent && !unlocked
        ? `<button class="att-start-btn" onclick="startAttunementQuest(${step.quest_id}, '${esc(step.name)}')">▶ Zahájit</button>`
        : ''}
    </div>`;
  }).join('');

  const dungeonBtn = unlocked
    ? `<button class="att-dungeon-btn" style="--att-color:${colorHex}" onclick="startAttunementQuest(${chain.dungeon_quest_id}, '${esc(chain.dungeon_name)}')">
        ${chain.dungeon_icon} Vstoupit do ${esc(chain.dungeon_name)}
        <span style="font-size:0.65rem;opacity:.7;margin-left:6px">⏱ ${chain.dungeon_duration}m · Lv.${chain.dungeon_min_level}+</span>
       </button>`
    : `<div class="att-dungeon-locked">
        ${chain.dungeon_icon} ${esc(chain.dungeon_name)}
        <span style="margin-left:8px;font-size:0.7rem;color:var(--text3)">Dokonči sérii pro přístup</span>
       </div>`;

  const statusBadge = unlocked
    ? `<span class="att-badge-unlocked">🔓 Odemčeno</span>`
    : `<span class="att-badge-locked">${chain.completed_steps}/${chain.total_steps} kroků</span>`;

  return `
    <div class="att-chain ${unlocked ? 'att-chain-unlocked' : ''}" style="--att-color:${colorHex}">
      <div class="att-chain-hdr">
        <div class="att-chain-badge">${chain.badge}</div>
        <div class="att-chain-info">
          <div class="att-chain-name">${esc(chain.name)}</div>
          <div class="att-chain-desc">${esc(chain.desc)}</div>
        </div>
        ${statusBadge}
      </div>

      <div class="att-progress-wrap">
        <div class="att-progress-track">
          <div class="att-progress-fill" style="width:${pct}%;background:${colorHex}"></div>
        </div>
        <span class="att-progress-pct">${pct}%</span>
      </div>

      <div class="att-steps">${stepsHtml}</div>

      <div class="att-dungeon-wrap">${dungeonBtn}</div>

      ${unlocked
        ? `<div class="att-reward-title">🏅 Titul odemčen: <strong style="color:${colorHex}">${esc(chain.reward_title)}</strong></div>`
        : ''}
    </div>`;
}

async function startAttunementQuest(questId, name) {
  try {
    const d = await api('POST', '/quest/start', { quest_id: questId });
    toast(`Quest "${name}" zahájen! ${d.success ? '✅ Výhra předpovězena' : '⚠ Bude to těžké'}`, 's', 3500);
    addAct(`⚔ Zahájen: ${name}`);
    await loadQuests();
    showPage('quests');
  } catch(e) { toast(e.message, 'e'); }
}
