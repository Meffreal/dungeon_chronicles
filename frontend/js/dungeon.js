// ── DUNGEON UI ────────────────────────────────────────────────────────────────
// Multi-stage dungeon systém.
// HP hráče se přenáší mezi stagy — žádná obnova.
// Stage 5 = boss s phase transitions.

let _dungeonRun         = null;
let _dungeonDcTimer     = null;
let _pendingStageResult = null;
let _dungeonModifier    = null;  // aktuální týdenní modifikátor

function showDungeonPage() {
  showPage('dungeons');
  loadBossDungeonData();
}

function switchDungeonTab(tab) {
  const bossContent    = document.getElementById('boss-dungeon-content');
  const classicContent = document.getElementById('dungeon-content');
  const bossTab        = document.getElementById('dtab-boss');
  const classicTab     = document.getElementById('dtab-classic');
  if (!bossContent || !classicContent) return;

  if (tab === 'boss') {
    bossContent.style.display    = '';
    classicContent.style.display = 'none';
    bossTab.classList.add('active');
    classicTab.classList.remove('active');
    loadBossDungeonData();
  } else {
    bossContent.style.display    = 'none';
    classicContent.style.display = '';
    bossTab.classList.remove('active');
    classicTab.classList.add('active');
    if (typeof loadDungeons === 'function') loadDungeons();
  }
}

async function loadDungeonData() {
  try {
    const [listData, statusData] = await Promise.all([
      api('GET', '/dungeon/list'),
      api('GET', '/dungeon/status'),
    ]);
    _dungeonRun      = statusData.run;
    _dungeonModifier = listData.modifier || null;
    renderDungeonPage(listData, statusData);
  } catch (e) {
    document.getElementById('dungeon-content').innerHTML =
      `<div class="empty-state">⚠️ Chyba načítání: ${esc(e.message || '')}</div>`;
  }
}

// ── Modifier banner helper ─────────────────────────────────────────────────────

function _buildModifierBanner(modifier) {
  if (!modifier) return '';

  const typeLabels = {
    enemy_buff:    'Nepřítel posílen',
    player_buff:   'Hráč posílen',
    player_debuff: 'Hráč oslaben',
    mixed:         'Smíšený',
    special:       'Speciální',
  };
  const typeLabel = typeLabels[modifier.type] || modifier.type;

  // Zbývající čas
  let timeStr = '';
  if (modifier.seconds_remaining > 0) {
    const h = Math.floor(modifier.seconds_remaining / 3600);
    const m = Math.floor((modifier.seconds_remaining % 3600) / 60);
    timeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  return `
    <div class="dng-modifier-banner" style="--mod-color: ${esc(modifier.color || '#888')}">
      <div class="dng-mod-icon">${esc(modifier.emoji || '❓')}</div>
      <div class="dng-mod-body">
        <div class="dng-mod-title">
          <span class="dng-mod-name">${esc(modifier.name)}</span>
          <span class="dng-mod-type-badge">${esc(typeLabel)}</span>
        </div>
        <p class="dng-mod-desc">${esc(modifier.description)}</p>
      </div>
      ${timeStr ? `<div class="dng-mod-timer">⏳ ${timeStr}</div>` : ''}
    </div>`;
}

function renderDungeonPage(listData, statusData) {
  const container = document.getElementById('dungeon-content');
  if (!container) return;

  const run = statusData.run;

  // Pokud máme aktivní run
  if (run && run.status === 'active') {
    renderActiveDungeon(run, listData?.modifier);
    return;
  }

  // Pokud máme dokončený/nesebraný run (nebo failed s nasbíranými odměnami)
  if (run && !run.reward_claimed && (run.status === 'completed' || (run.status === 'failed' && (run.reward_xp > 0 || run.reward_gold > 0)))) {
    renderDungeonReady(run);
    return;
  }

  // Zobraz list dungeonů
  renderDungeonList(listData.dungeons || [], listData.modifier);
}

// ── Dungeon list ───────────────────────────────────────────────────────────────

// ── Dungeon visual config ──
const DNG_ART_MAP = {
  catacombs: { artClass:'dng-gate-art--catacombs', color:'#40b840', rgb:'64,184,64' },
  tower:     { artClass:'dng-gate-art--tower',     color:'#e05020', rgb:'224,80,32' },
  ice:       { artClass:'dng-gate-art--ice',       color:'#60c8f0', rgb:'96,200,240' },
};
function _dngArt(dungeonKey) {
  const k = (dungeonKey || '').toLowerCase();
  if (k.includes('catacomb') || k.includes('katakomb')) return DNG_ART_MAP.catacombs;
  if (k.includes('tower') || k.includes('vez'))         return DNG_ART_MAP.tower;
  if (k.includes('ice') || k.includes('led'))           return DNG_ART_MAP.ice;
  return { artClass:'dng-gate-art--dark', color:'#c8a050', rgb:'200,160,80' };
}

function renderDungeonList(dungeons, modifier) {
  const container = document.getElementById('dungeon-content');
  if (!container) return;

  const cards = dungeons.map((d, i) => {
    const art        = _dngArt(d.key);
    const locked     = !!d.level_required;
    const onCd       = !d.can_enter && !d.level_required;
    const hasActive  = d.has_active_run;
    const totalStages = d.stages || 5;
    const currentStage = hasActive ? (d.active_run_stage || 1) : 0;

    // Stage dots (poslední = boss)
    const dots = Array.from({length: totalStages}, (_, s) => {
      const num    = s + 1;
      const isBoss = num === totalStages;
      const done   = num < currentStage;
      return `<div class="dng-stage-dot ${isBoss?'boss':''} ${done?'done':''}"></div>`;
    }).join('');

    // Action button
    let btn = '';
    if (hasActive) {
      btn = `<button class="dng-gate-btn dng-gate-btn--enter"
               onclick="resumeDungeon('${esc(d.key)}')">
               ▶ Pokračovat (${d.active_run_stage}/${totalStages})
             </button>`;
    } else if (locked) {
      btn = `<button class="dng-gate-btn" disabled>⛔ Vyžaduje Lv. ${d.min_level}</button>`;
    } else if (onCd) {
      btn = `<button class="dng-gate-btn" disabled>
               ⏳ <span class="dng-cd-timer" data-seconds="${d.cd_remaining}">${_formatCd(d.cd_remaining)}</span>
             </button>`;
    } else {
      btn = `<button class="dng-gate-btn dng-gate-btn--enter"
               onclick="enterDungeon('${esc(d.key)}', this)">
               ⚔ Vstoupit
             </button>`;
    }

    return `
      <div class="dng-gate ${locked?'dng-gate--locked':''} ${hasActive?'dng-gate--active':''}"
           style="--dng-color:${art.color};--dng-rgb:${art.rgb};animation-delay:${i*0.09}s">
        <div class="dng-gate-art ${art.artClass}"></div>
        ${hasActive ? `<div class="dng-gate-active-badge">▶ Aktivní run</div>` : ''}
        <div class="dng-gate-content">
          <div class="dng-gate-top">
            <div class="dng-gate-emoji">${esc(d.emoji)}</div>
            <div class="dng-gate-info">
              <div class="dng-gate-name">${esc(d.name)}</div>
              <div class="dng-gate-desc">${esc(d.description)}</div>
              <div class="dng-gate-meta">
                <span class="dng-gate-tag">Lv. ${d.min_level}+</span>
                <span class="dng-gate-tag">${totalStages} stagů</span>
              </div>
            </div>
          </div>
          <div class="dng-stage-dots">${dots}</div>
          <div class="dng-gate-rewards">
            <span class="dng-gate-reward">🏆 ${d.rewards_preview?.completion_xp||0} XP</span>
            <span class="dng-gate-reward">💰 ${d.rewards_preview?.completion_gold||0} G</span>
            <span class="dng-gate-reward">🗡 Bonus item</span>
          </div>
          ${btn}
        </div>
        ${locked ? `<div class="dng-gate-lock-overlay"><div class="dng-gate-lock-icon">🔒</div></div>` : ''}
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="dng-page">
      ${_buildModifierBanner(modifier)}
      <div class="dng-gate-grid">
        ${cards || '<p class="empty-state">Žádné dungeony dostupné.</p>'}
      </div>
    </div>`;

  // Cooldown timery
  document.querySelectorAll('.dng-cd-timer').forEach(el => {
    let secs = parseInt(el.dataset.seconds || '0');
    if (secs <= 0) return;
    const iv = setInterval(() => {
      secs--;
      el.textContent = _formatCd(secs);
      if (secs <= 0) { clearInterval(iv); loadDungeons(); }
    }, 1000);
  });
}

// ── Aktivní dungeon run ────────────────────────────────────────────────────────

function renderActiveDungeon(run, modifier) {
  const container = document.getElementById('dungeon-content');
  if (!container) return;

  const ddef    = _getDungeonDef(run);
  const stages  = ddef?.stages || [];
  const stageDef = stages.find(s => s.stage_num === run.current_stage);
  const hpPct   = run.player_hp_pct || 0;

  const stageProgress = _buildStageProgress(run.current_stage, run.total_stages, stages, run);

  // Modifier badge — malý inline badge pro aktivní run
  const modBadge = modifier
    ? `<div class="dng-mod-badge" style="--mod-color: ${esc(modifier.color || '#888')}" title="${esc(modifier.description)}">
         ${esc(modifier.emoji)} ${esc(modifier.name)}
       </div>`
    : '';

  container.innerHTML = `
    <div class="dng-active-wrapper">
      <div class="dng-active-header">
        <span class="dng-emoji">${esc(run.dungeon_emoji || '🗝')}</span>
        <div>
          <h2>${esc(run.dungeon_name)}</h2>
          <p>${esc(run.current_stage_name || '')}</p>
        </div>
        ${modBadge}
      </div>

      <!-- Stage progress -->
      ${stageProgress}

      <!-- Hráčovo HP -->
      <div class="dng-player-hp">
        <div class="dng-hp-label">
          <span>❤ HP hráče</span>
          <span>${run.player_hp_current} / ${run.player_hp_max}</span>
        </div>
        <div class="dng-hp-track">
          <div class="dng-hp-fill ${hpPct < 30 ? 'dng-hp-critical' : ''}"
               style="width:${hpPct}%"></div>
        </div>
      </div>

      <!-- Accumulated rewards -->
      <div class="dng-rewards-acc">
        <span>🏆 Nasbírané XP: <strong>${run.reward_xp}</strong></span>
        <span>💰 Nasbírané G: <strong>${run.reward_gold}</strong></span>
      </div>

      <!-- Akce -->
      <div class="dng-actions">
        ${run.secret_path_offered && run.current_stage === 2
          ? `<button class="btn btn-warning btn-lg" onclick="_showSecretPathDialog(${run.id})" id="dng-next-btn">
               ❓ Tajný průchod — rozhodni!
             </button>`
          : run.current_stage < run.total_stages
            ? `<button class="btn btn-danger btn-lg" onclick="dungeonNextStage(${run.id})" id="dng-next-btn">
                 ▶ Pokračovat na Stage ${run.current_stage + 1} — ${esc(stages[run.current_stage]?.name || '')}
               </button>`
            : `<button class="btn btn-gold btn-lg" onclick="dungeonNextStage(${run.id})" id="dng-next-btn">
                 ⚔ Finální Boss! — ${esc(stageDef?.enemy_name || 'Boss')}
               </button>`}
        <button class="btn btn-ghost" onclick="abandonDungeon(${run.id})">
          ✕ Opustit dungeon
        </button>
      </div>
      <!-- Combat Insights po stage (populates dynamically) -->
      <div id="dng-stage-insights"></div>
    </div>`;
}

function _buildStageProgress(currentStage, totalStages, stages, run) {
  const items = stages.map((s, i) => {
    const done    = s.stage_num < currentStage;
    const current = s.stage_num === currentStage;
    const typeClass = s.type === 'boss' ? 'dng-stage-boss'
      : s.type === 'miniboss' ? 'dng-stage-miniboss'
      : s.type === 'elite' ? 'dng-stage-elite'
      : 'dng-stage-normal';

    // Secret path badge — stage 3
    const secretOffer = run && s.stage_num === 3 && run.secret_path_offered && !run.secret_path_taken && currentStage === 2;
    const secretTaken = run && s.stage_num === 3 && run.secret_path_taken;

    return `
      <div class="dng-stage-node ${done ? 'dng-stage-done' : ''} ${current ? 'dng-stage-current' : ''} ${typeClass} ${secretTaken ? 'dng-stage-secret' : ''}">
        <div class="dng-stage-icon">${secretTaken ? '🗝' : done ? '✓' : s.stage_num}</div>
        <div class="dng-stage-name">${esc(s.name)}</div>
        ${s.type === 'boss' ? '<div class="dng-stage-boss-badge">BOSS</div>' : ''}
        ${s.type === 'miniboss' ? '<div class="dng-stage-boss-badge" style="background:#e67e22">MINI</div>' : ''}
        ${secretOffer ? '<div class="dng-stage-secret-badge">❓</div>' : ''}
        ${secretTaken ? '<div class="dng-stage-secret-badge dng-secret-taken">🗝</div>' : ''}
      </div>`;
  });

  return `
    <div class="dng-progress">
      ${items.map((item, i) => `
        ${item}
        ${i < stages.length - 1 ? `<div class="dng-stage-connector ${i < currentStage - 1 ? 'done' : ''}"></div>` : ''}
      `).join('')}
    </div>`;
}

function renderDungeonReady(run) {
  const container = document.getElementById('dungeon-content');
  if (!container) return;

  container.innerHTML = `
    <div class="dng-completed-wrapper">
      <div class="dng-completed-icon">${run.status === 'failed' ? '⚠' : '🏆'}</div>
      <h2>${esc(run.dungeon_name)} — ${run.status === 'failed' ? 'Nashromážděné odměny' : 'Dokončeno!'}</h2>
      <div class="dng-final-rewards">
        <div class="dng-reward-item">
          <span class="dng-reward-ico">✨</span>
          <span class="dng-reward-val">+${run.reward_xp} XP</span>
        </div>
        <div class="dng-reward-item">
          <span class="dng-reward-ico">💰</span>
          <span class="dng-reward-val">+${run.reward_gold} G</span>
        </div>
        <div class="dng-reward-item">
          <span class="dng-reward-ico">🗡</span>
          <span class="dng-reward-val">Bonus item!</span>
        </div>
      </div>
      <button class="btn btn-gold btn-lg" onclick="collectDungeon(${run.id})">
        🏆 Vyzvednout odměny
      </button>
    </div>`;
}

// ── Akce ───────────────────────────────────────────────────────────────────────

async function enterDungeon(dungeonKey, btnEl) {
  // Guard: konkrétní tlačítko — zamezí double-click i přepisu nesprávného tlačítka
  const btn = btnEl instanceof HTMLElement ? btnEl : document.querySelector(`.dng-card .btn-danger`);
  if (btn && btn.disabled) return;
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Vstupuji...'; }

  try {
    const result = await api('POST', '/dungeon/enter', { dungeon_key: dungeonKey });
    _dungeonRun  = result.run;

    // Zobraz combat replay stage 1
    _showStageReplay(result, 1);

  } catch (e) {
    toast(e.message || 'Vstup do dungeonu selhal.', 'e');
    if (btn) { btn.disabled = false; btn.textContent = '⚔ Vstoupit'; }
    await loadDungeons();
  }
}

async function resumeDungeon(dungeonKey) {
  await loadDungeons();
}

async function dungeonNextStage(runId) {
  const btn = document.getElementById('dng-next-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Bojuji...'; }

  try {
    const result = await api('POST', '/dungeon/next-stage', { run_id: runId });
    _dungeonRun  = result.run;

    // Fáze A: tajný průchod nabídnut — zobraz dialog (no combat yet)
    if (result.requires_choice) {
      _showSecretPathDialog(runId);
      return;
    }

    _showStageReplay(result, result.stage_num);

  } catch (e) {
    toast(e.message || 'Postup na další stage selhal.', 'e');
    await loadDungeons();
  }
}

async function dungeonAcceptSecretPath(runId, accept) {
  // Skryj dialog a bojuj s volbou
  const overlay = document.getElementById('dng-secret-overlay');
  if (overlay) overlay.remove();

  const btn = document.getElementById('dng-next-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Bojuji...'; }

  try {
    const result = await api('POST', '/dungeon/next-stage', {
      run_id: runId,
      accept_secret: accept,
    });
    _dungeonRun = result.run;

    if (accept && result.was_secret) {
      toast('🗝 Tajný průchod — souboj začíná!', 'i', 3000);
    }
    _showStageReplay(result, result.stage_num);

  } catch (e) {
    toast(e.message || 'Postup na tajný stage selhal.', 'e');
    await loadDungeons();
  }
}

function _showSecretPathDialog(runId) {
  // Odstraň existující overlay
  const old = document.getElementById('dng-secret-overlay');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'dng-secret-overlay';
  overlay.className = 'dng-secret-overlay';
  overlay.innerHTML = `
    <div class="dng-secret-dialog">
      <div class="dng-secret-icon">❓</div>
      <h3 class="dng-secret-title">Tajný průchod nalezen!</h3>
      <p class="dng-secret-desc">
        Za skrytými dveřmi číhá <strong>silnější nepřítel</strong>,
        ale kořist je <strong>dvojnásobná</strong>. Riskuješ?
      </p>
      <div class="dng-secret-rewards">
        <span class="dng-secret-pill dng-secret-danger">⚔ +60% síla nepřítele</span>
        <span class="dng-secret-pill dng-secret-bonus">💰 ×2 odměna</span>
      </div>
      <div class="dng-secret-btns">
        <button class="btn btn-danger" onclick="dungeonAcceptSecretPath(${runId}, true)">
          🗝 Vstoupit do tajného průchodu
        </button>
        <button class="btn btn-ghost" onclick="dungeonAcceptSecretPath(${runId}, false)">
          ➡ Pokračovat normálně
        </button>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

async function collectDungeon(runId) {
  try {
    const result = await api('POST', '/dungeon/collect', { run_id: runId });
    if (result.character) updateUI(result.character);

    let msg = `🏆 Dungeon dokončen! +${result.xp_gained} XP, +${result.gold_gained} G`;
    if (result.item) msg += `, 🗡 ${result.item.name}`;
    toast(msg, 's', 6000);

    if (result.leveled_up?.length) {
      toast(`⬆ Level UP! Dosáhl jsi level ${result.leveled_up.at(-1)}!`, 's', 5000);
    }

    await loadDungeons();
  } catch (e) {
    toast(e.message || 'Nelze vyzvednout odměny.', 'e');
  }
}

async function abandonDungeon(runId) {
  if (!confirm('Opravdu chceš opustit dungeon? Ztratíš veškerý progress.')) return;
  try {
    await api('POST', '/dungeon/abandon', { run_id: runId });
    toast('Dungeon opuštěn.', 'i');
    await loadDungeons();
  } catch (e) {
    toast(e.message || 'Opuštění selhalo.', 'e');
  }
}

// ── Stage replay ───────────────────────────────────────────────────────────────

function _showStageReplay(result, stageNum) {
  const isBoss    = stageNum === (result.run?.total_stages || 5);
  const stageName = result.stage_name || `Stage ${stageNum}`;
  const _evts     = result.events || null;
  const _won      = result.player_won;

  showCombatReplay(
    result.events || result.battle_log,
    char?.name || 'Hráč',
    result.enemy_name || 'Nepřítel',
    result.player_won,
    result.run?.player_hp_max || char?.combat?.hp_max || 100,
    result.enemy_hp_max || 100,
    {
      isBoss: isBoss,
      title:  `${result.run?.dungeon_emoji || '🗝'} ${stageName}`,
      rewards: result.player_won ? {
        xp:   result.stage_xp   || 0,
        gold: result.stage_gold || 0,
      } : null,
    }
  );

  // Po zavření replay aktualizuj UI a zobraz insights
  setTimeout(async () => {
    if (result.dungeon_completed) {
      renderDungeonReady(result.run);
    } else if (!result.player_won && result.permadeath) {
      // HC permadeath — zobraz death screen
      if (typeof showDeathScreen === 'function') {
        showDeathScreen({
          name:        result.hero_name,
          level:       result.hero_level,
          cls:         result.hero_cls,
          killed_by:   result.killed_by,
          days_survived: result.days_survived,
        });
      }
    } else if (!result.player_won) {
      toast(`💀 Poražen v ${stageName}. Dungeon selhal.`, 'e', 5000);
      await loadDungeons();
    } else {
      renderActiveDungeon(result.run, _dungeonModifier);
      // Naplní insights kontejner vložený v renderActiveDungeon
      if (typeof showCombatInsights === 'function' && _evts?.length) {
        setTimeout(() => {
          showCombatInsights('dng-stage-insights', _evts, _won,
            char?.name || 'Hráč', char?.cls, null);
        }, 50);
      }
    }
  }, 1200);
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function _getDungeonDef(run) {
  if (!run) return null;
  // DUNGEON_DATA je globální z dungeons.js, naplněno z /dungeon/config
  if (typeof DUNGEON_DATA !== 'undefined' && DUNGEON_DATA.length > 0) {
    return DUNGEON_DATA.find(d => d.dungeon_key === run.dungeon_key) || null;
  }
  return null;
}

function _formatCd(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

// ── Boss Dungeon System ────────────────────────────────────────────────────────

let _bossListData   = null;   // response from /dungeon/boss/list
let _bossCdTimer    = null;   // interval for countdown

async function loadBossDungeonData() {
  try {
    const data = await api('GET', '/dungeon/boss/list');
    _bossListData = data;
    renderBossDungeonList(data);
  } catch (e) {
    const c = document.getElementById('boss-dungeon-content');
    if (c) c.innerHTML = `<div class="empty-state">⚠️ ${esc(e.message || 'Chyba načítání')}</div>`;
  }
}

function renderBossDungeonList(data) {
  const container = document.getElementById('boss-dungeon-content');
  if (!container) return;

  const { dungeons, on_cooldown, cd_remaining } = data;

  let cdBanner = '';
  if (on_cooldown && cd_remaining > 0) {
    const h = Math.floor(cd_remaining / 3600);
    const m = Math.floor((cd_remaining % 3600) / 60);
    const s = cd_remaining % 60;
    cdBanner = `
      <div class="boss-cd-banner">
        ⏳ Cooldown: <span id="boss-cd-countdown">${h}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s</span>
      </div>`;
    _startBossCdCountdown(cd_remaining);
  }

  const dungeonCards = dungeons.map(d => `
    <div class="boss-dungeon-card ${d.is_unlocked ? '' : 'locked'}"
         ${d.is_unlocked ? `onclick="openBossDungeon('${d.key}')"` : ''}>
      <div class="bdc-header">
        <span class="bdc-emoji">${esc(d.emoji)}</span>
        <div class="bdc-info">
          <h3 class="bdc-name">${esc(d.name)}</h3>
          <p class="bdc-desc">${esc(d.description)}</p>
        </div>
      </div>
      <div class="bdc-progress-bar">
        <div class="bdc-progress-fill" style="width:${d.progress_pct}%"></div>
      </div>
      <div class="bdc-footer">
        <span class="bdc-progress-text">${d.highest_boss}/${d.total_bosses} bosses</span>
        ${d.is_unlocked
          ? (d.next_boss_num
              ? `<span class="bdc-next">Next: #${d.next_boss_num}</span>`
              : `<span class="bdc-complete">✅ Complete</span>`)
          : `<span class="bdc-lock">🔒 ${esc(d.lock_reason)}</span>`
        }
      </div>
    </div>
  `).join('');

  container.innerHTML = cdBanner + `<div class="boss-dungeon-list">${dungeonCards}</div>`;
}

function _startBossCdCountdown(seconds) {
  if (_bossCdTimer) clearInterval(_bossCdTimer);
  let remaining = seconds;
  _bossCdTimer = setInterval(() => {
    remaining--;
    const el = document.getElementById('boss-cd-countdown');
    if (!el || remaining <= 0) {
      clearInterval(_bossCdTimer);
      if (remaining <= 0) loadBossDungeonData();
      return;
    }
    const h = Math.floor(remaining / 3600);
    const m = Math.floor((remaining % 3600) / 60);
    const s = remaining % 60;
    el.textContent = `${h}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`;
  }, 1000);
}

async function openBossDungeon(dungeonKey) {
  try {
    const c = document.getElementById('boss-dungeon-content');
    if (c) c.innerHTML = '<div class="empty-state">Načítání...</div>';
    const data = await api('GET', `/dungeon/boss/bosses/${dungeonKey}`);
    renderBossList(data);
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

function renderBossList(data) {
  const container = document.getElementById('boss-dungeon-content');
  if (!container) return;

  const { dungeon_key, dungeon_name, dungeon_emoji, highest_boss, bosses } = data;

  const bossRows = bosses.map(b => {
    const stateClass = b.defeated ? 'defeated' : b.is_next ? 'available' : 'locked';
    const icon = b.defeated ? '✅' : b.is_next ? '⚔️' : b.is_locked ? '🔒' : '❓';
    const milestone = b.is_milestone ? ' <span class="milestone-badge">★</span>' : '';
    return `
      <div class="boss-row ${stateClass}"
           ${b.is_next ? `onclick="fightBoss('${dungeon_key}', ${b.num})"` : ''}>
        <span class="boss-num">#${b.num}</span>
        <span class="boss-icon">${icon}</span>
        <div class="boss-info">
          <span class="boss-name">${esc(b.name)}${milestone}</span>
          <span class="boss-desc">${esc(b.desc)}</span>
        </div>
        <span class="boss-mult">×${b.enemy_mult}</span>
      </div>`;
  }).join('');

  container.innerHTML = `
    <div class="boss-list-header">
      <button class="btn-back" onclick="loadBossDungeonData()">← Zpět</button>
      <h2>${esc(dungeon_emoji)} ${esc(dungeon_name)}</h2>
      <span class="boss-progress-badge">${highest_boss}/50</span>
    </div>
    <div class="boss-list">${bossRows}</div>`;
}

async function fightBoss(dungeonKey, bossNum) {
  const rows = document.querySelectorAll('.boss-row.available');
  rows.forEach(r => r.onclick = null);

  try {
    const data = await api('POST', '/dungeon/boss/fight', {
      dungeon_key: dungeonKey,
      boss_num: bossNum,
    });

    if (data.result === 'victory') {
      const { rewards, boss_name } = data;
      let msg = `✅ ${esc(boss_name)} poražen! +${rewards.xp} XP, +${rewards.gold} 🪙`;
      if (rewards.item_drop) {
        msg += ` | 🎁 ${esc(rewards.item_drop.name)} (${esc(rewards.item_drop.rarity)})`;
      }
      toast(msg, 's', 5000);

      if (rewards.leveled_up) {
        toast(`🎉 Level up! Jsi nyní level ${rewards.new_level}!`, 's', 4000);
      }

      const updatedChar = await api('GET', '/character/me');
      updateUI(updatedChar);

      _showBossCombatLog(data);

    } else {
      const msg = data.permadeath
        ? `💀 ${esc(data.boss_name)} tě zabil! PERMADEATH!`
        : `☠️ ${esc(data.boss_name)} tě porazil.`;
      toast(msg, 'e', 5000);
      _showBossCombatLog(data);

      if (data.permadeath) {
        setTimeout(() => location.reload(), 3000);
        return;
      }
    }

    await openBossDungeon(dungeonKey);

  } catch (e) {
    toast(e.message || 'Chyba', 'e');
    await openBossDungeon(dungeonKey);
  }
}

function _showBossCombatLog(data) {
  if (typeof showCombatResult === 'function') {
    showCombatResult(data.combat_log, data.events, data.result === 'victory');
  }
}
