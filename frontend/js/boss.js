// ── WORLD BOSS UI ─────────────────────────────────────────────────────────────
// Zobrazuje aktuálního World Bosse, HP bar, cooldown, leaderboard.
// Hráč útočí jednou za 6 hodin — přispívá do sdíleného HP poolu.

let _bossData       = null;
let _bossCdInterval = null;
let _bossLbInterval = null;   // 30s leaderboard polling

async function showBossPage() {
  showPage('boss');
  await loadBossData();
  _startBossLbPolling();
}

function _startBossLbPolling() {
  if (_bossLbInterval) clearInterval(_bossLbInterval);
  _bossLbInterval = setInterval(async () => {
    // Zastavit polling pokud jsme opustili boss stránku
    const page = document.getElementById('page-boss');
    if (!page || page.style.display === 'none') {
      clearInterval(_bossLbInterval);
      _bossLbInterval = null;
      return;
    }
    try {
      const data = await api('GET', '/boss/leaderboard');
      if (data.leaderboard) {
        const mvpEl = document.getElementById('boss-mvp-banner');
        if (mvpEl) mvpEl.outerHTML = _buildDailyMvpBanner(data.leaderboard);
        const lbEl = document.getElementById('boss-lb-container');
        if (lbEl) lbEl.innerHTML = _buildBossLeaderboard(data.leaderboard);
      }
    } catch { /* tiché selhání */ }
  }, 30000);
}

async function loadBossData() {
  try {
    const data = await api('GET', '/boss/current');
    _bossData  = data;
    renderBossPage(data);
  } catch (e) {
    document.getElementById('boss-content').innerHTML =
      `<div class="empty-state">⚠️ Nepodařilo se načíst data bosse: ${esc(e.message || '')}</div>`;
  }
}

function renderBossPage(data) {
  const container = document.getElementById('boss-content');
  if (!container) return;

  if (!data.boss) {
    container.innerHTML = `
      <div class="empty-state">
        <div style="font-size:3rem">💀</div>
        <h3>Žádný aktivní boss</h3>
        <p>World Boss se brzy znovu objeví. Sleduj zprávy!</p>
      </div>`;
    return;
  }

  const boss = data.boss;
  const hpPct = Math.max(0, Math.min(100, boss.hp_pct));
  const hpBarColor = hpPct > 60 ? '#e74c3c' : hpPct > 30 ? '#e67e22' : '#c0392b';

  const phaseHtml = _buildPhaseIndicator(boss);
  const lbHtml    = _buildBossLeaderboard(data.leaderboard || []);
  const cdHtml    = _buildCooldownBlock(data);

  container.innerHTML = `
    <div class="boss-wrapper">
      <!-- Boss card -->
      <div class="boss-card">
        <div class="boss-header">
          <span class="boss-emoji">${esc(boss.emoji)}</span>
          <div class="boss-title-block">
            <h2 class="boss-name">${esc(boss.name)}</h2>
            <p class="boss-desc">${esc(boss.description || '')}</p>
          </div>
          ${boss.is_alive
            ? `<div class="boss-alive-badge">⚔ ŽIVÝ</div>`
            : `<div class="boss-dead-badge">💀 PORAŽEN</div>`}
        </div>

        <!-- Boss HP bar -->
        <div class="boss-hp-section">
          <div class="boss-hp-labels">
            <span>HP Bosse</span>
            <span class="boss-hp-numbers">${boss.hp_current.toLocaleString()} / ${boss.hp_max.toLocaleString()}</span>
          </div>
          <div class="boss-hp-track">
            <div class="boss-hp-fill" id="boss-hp-fill"
                 style="width:${hpPct}%; background:${hpBarColor}">
              <span class="boss-hp-pct">${hpPct.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <!-- Fáze bosse -->
        ${phaseHtml}

        <!-- Mé příspěvky -->
        <div class="boss-my-stats">
          <span>💥 Mé poškození: <strong>${(data.my_damage || 0).toLocaleString()}</strong></span>
          <span>⚔ Mé útoky: <strong>${data.my_attacks || 0}</strong></span>
        </div>

        <!-- Attack button / cooldown -->
        ${cdHtml}
      </div>

      <!-- Leaderboard -->
      <div class="boss-leaderboard-card">
        <div id="boss-mvp-banner">${_buildDailyMvpBanner(data.leaderboard || [])}</div>
        <h3>🏆 Top přispěvatelé</h3>
        <div id="boss-lb-container">${lbHtml}</div>
      </div>
    </div>
  `;

  // Start cooldown timer
  _startBossCooldownTimer(data.cd_remaining || 0);

  // Claim button pokud boss zabit a hráč přispěl
  if (!boss.is_alive && data.my_damage > 0) {
    _checkBossRewards();
  }
}

function _buildPhaseIndicator(boss) {
  if (!boss.phases_total || boss.phases_total === 0) return '';
  const phases = [];
  for (let i = 1; i <= boss.phases_total; i++) {
    const active  = boss.current_phase >= i;
    const current = boss.current_phase === i;
    phases.push(`
      <div class="boss-phase ${active ? 'boss-phase-active' : ''} ${current ? 'boss-phase-current' : ''}">
        <span class="boss-phase-num">${i}</span>
        <span class="boss-phase-label">Fáze ${i}</span>
      </div>`);
  }
  return `
    <div class="boss-phases-section">
      <span class="boss-phases-label">Fáze bosse:</span>
      <div class="boss-phases">${phases.join('')}</div>
      ${boss.current_phase > 0
        ? `<div class="boss-phase-msg">⚡ Fáze ${boss.current_phase} aktivní!</div>`
        : ''}
    </div>`;
}

function _buildDailyMvpBanner(leaderboard) {
  const mvp = leaderboard.find(e => e.is_daily_mvp);
  if (!mvp || !mvp.daily_damage) return '<div></div>';
  return `
    <div class="boss-mvp-banner">
      <span class="boss-mvp-crown">👑</span>
      <span class="boss-mvp-label">Denní MVP</span>
      <span class="boss-mvp-sep">·</span>
      <span class="boss-mvp-name">${esc(mvp.name)}</span>
      <span class="boss-mvp-dmg">${mvp.daily_damage.toLocaleString('cs')} dmg dnes</span>
      <span class="boss-mvp-reward">+100 G bonus při zabití</span>
    </div>`;
}

function _buildBossLeaderboard(leaderboard) {
  if (!leaderboard.length) return '<p class="empty-state">Zatím žádní útočníci.</p>';

  const rows = leaderboard.map(e => `
    <tr class="${e.is_me ? 'lb-me' : ''} ${e.is_daily_mvp ? 'lb-mvp' : ''}">
      <td>${e.is_daily_mvp ? '<span class="lb-mvp-crown">👑</span>' : e.rank}</td>
      <td>
        ${esc(e.name)}${e.is_me ? ' <span class="lb-you">(ty)</span>' : ''}
        ${e.cls_emoji ? `<span class="lb-cls">${e.cls_emoji}</span>` : ''}
      </td>
      <td>${e.damage.toLocaleString('cs')}</td>
      <td class="${e.is_daily_mvp ? 'lb-daily-mvp' : 'lb-daily'}">
        ${e.daily_damage > 0 ? e.daily_damage.toLocaleString('cs') : '<span class="lb-none">—</span>'}
      </td>
      <td>
        <div class="lb-contrib-bar">
          <div class="lb-contrib-fill" style="width:${e.contribution_pct}%"></div>
          <span>${e.contribution_pct}%</span>
        </div>
      </td>
    </tr>`).join('');

  return `
    <table class="lb-table">
      <thead>
        <tr><th>#</th><th>Hráč</th><th>Celkem</th><th>Dnes</th><th>Příspěvek</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function _buildCooldownBlock(data) {
  if (!data.boss?.is_alive) {
    if (data.my_damage > 0) {
      return `
        <div class="boss-action-block">
          <button class="btn btn-gold" onclick="claimBossRewards()">
            🏆 Vyzvednout odměny
          </button>
        </div>`;
    }
    return `<div class="boss-action-block boss-dead-msg">Boss byl poražen. Brzy se objeví nový.</div>`;
  }

  const minLevel = data.min_level || 1;
  if (data.char_level < minLevel) {
    return `<div class="boss-action-block boss-level-req">
      ⛔ Vyžaduje Level ${minLevel} (tvůj level: ${data.char_level})
    </div>`;
  }

  if (!data.can_attack) {
    const cd = data.cd_remaining || 0;
    return `
      <div class="boss-action-block">
        <button class="btn btn-secondary" disabled id="boss-attack-btn">
          ⏳ Cooldown: <span id="boss-cd-timer">${_formatCd(cd)}</span>
        </button>
        <p class="boss-cd-note">Příští útok dostupný za <span id="boss-cd-full">${_formatCdFull(cd)}</span></p>
      </div>`;
  }

  return `
    <div class="boss-action-block">
      <button class="btn btn-danger btn-lg" onclick="attackBoss()" id="boss-attack-btn">
        ⚔ Zaútočit na ${esc(data.boss?.name || 'Bosse')}
      </button>
      <p class="boss-attack-note">Útok spotřebuje 6h cooldown</p>
    </div>`;
}

function _startBossCooldownTimer(seconds) {
  if (_bossCdInterval) clearInterval(_bossCdInterval);
  if (seconds <= 0) return;

  let remaining = seconds;
  _bossCdInterval = setInterval(() => {
    remaining--;
    const timerEl = document.getElementById('boss-cd-timer');
    const fullEl  = document.getElementById('boss-cd-full');
    if (timerEl) timerEl.textContent = _formatCd(remaining);
    if (fullEl)  fullEl.textContent  = _formatCdFull(remaining);

    if (remaining <= 0) {
      clearInterval(_bossCdInterval);
      // Reload boss page — cooldown skončil
      loadBossData();
    }
  }, 1000);
}

function _formatCd(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function _formatCdFull(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} hodiny ${m} minut`;
  if (m > 0) return `${m} minut`;
  return `${seconds} sekund`;
}

// ── Attack ─────────────────────────────────────────────────────────────────────

async function attackBoss() {
  const btn = document.getElementById('boss-attack-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⚔ Útočím...'; }

  try {
    const result = await api('POST', '/boss/attack');

    // Aktualizuj char data
    if (result.character) updateUI(result.character);

    // Zobraz combat replay
    const enemyName = _bossData?.boss?.name || 'Boss';
    showCombatReplay(
      result.events || result.battle_log,
      char?.name || 'Hráč',
      enemyName,
      result.player_won,
      result.player_hp_max,
      result.enemy_hp_max,
      {
        isBoss: true,
        bossEmoji: _bossData?.boss?.emoji || '💀',
        title: `⚔ Útok na ${enemyName}`,
        rewards: {
          damage: result.damage_dealt,
        },
      }
    );

    if (result.boss_killed) {
      toast(`💀 ${enemyName} byl poražen! Vyzvednul si odměny.`, 's', 5000);
    } else {
      const dmg = result.damage_dealt || 0;
      toast(`⚔ Způsobil jsi ${dmg.toLocaleString()} poškození! HP bosse: ${result.boss_hp_pct}%`, 'i', 4000);
    }

    // Reload po zavření replay
    setTimeout(() => loadBossData(), 1500);

  } catch (e) {
    toast(e.message || 'Útok selhal.', 'e');
    if (btn) { btn.disabled = false; btn.textContent = '⚔ Zaútočit'; }
  }
}

// ── Claim rewards ──────────────────────────────────────────────────────────────

async function claimBossRewards() {
  try {
    const result = await api('POST', '/boss/claim');
    if (result.character) updateUI(result.character);
    toast(`🏆 Boss odměny: +${result.xp_gained} XP, +${result.gold_gained} G`, 's', 5000);
    if (result.leveled_up?.length) {
      toast(`⬆ Level UP! Dosáhl jsi level ${result.leveled_up.at(-1)}!`, 's', 5000);
    }
    await loadBossData();
  } catch (e) {
    toast(e.message || 'Nelze vyzvednout odměny.', 'e');
  }
}

async function _checkBossRewards() {
  // Přidá claim button pokud jsou nevyzvednuté odměny
  // (Volá se z renderBossPage — UI se řídí daty z /boss/current)
}
