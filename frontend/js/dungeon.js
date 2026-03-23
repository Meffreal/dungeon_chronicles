// ── DUNGEON BOSS ENCOUNTERS ───────────────────────────────────────────────────
// Zone boss list + boss fight. World map je v dungeons.js.

let _bossCdTimer = null;

function showDungeonPage() {
  showPage('dungeons');
  loadDungeons();
}

// ── Single boss encounter view ────────────────────────────────────────────────

async function openZoneBossView(dungeonKey) {
  const c = document.getElementById('dungeon-content');
  if (c) c.innerHTML = '<div class="empty-state">Načítání...</div>';
  try {
    const data = await api('GET', `/dungeon/boss/bosses/${dungeonKey}`);
    renderBossEncounter(data);
  } catch (e) {
    toast(e.message || 'Chyba načítání zóny.', 'e');
    loadDungeons();
  }
}

function renderBossEncounter(data) {
  const container = document.getElementById('dungeon-content');
  if (!container) return;

  const { dungeon_key, dungeon_name, dungeon_emoji, highest_boss, total_bosses,
          completed, on_cooldown, cd_remaining, current_boss } = data;

  // Dungeon completed
  if (completed) {
    container.innerHTML = `
      <div class="boss-encounter-wrap">
        <div class="boss-encounter-header">
          <button class="btn-back" onclick="loadDungeons()">← Mapa</button>
          <span class="boss-zone-label">${esc(dungeon_emoji)} ${esc(dungeon_name)}</span>
          <span class="boss-progress-badge">${total_bosses}/${total_bosses}</span>
        </div>
        <div class="boss-encounter-card completed">
          <div class="bec-icon">🏆</div>
          <div class="bec-name">Zóna dokončena!</div>
          <div class="bec-desc">Porazil jsi všech ${total_bosses} bossů.</div>
        </div>
      </div>`;
    return;
  }

  const b   = current_boss;
  const { hp, atk, def: def_, spd, mult } = b.stats;
  const floorLabel   = `${b.num} / ${total_bosses}`;
  const milestoneBadge = b.is_milestone
    ? '<span class="bec-milestone-badge">★ Milestone — garantovaný drop</span>'
    : '';

  let cdHtml = '';
  if (on_cooldown && cd_remaining > 0) {
    const h = Math.floor(cd_remaining / 3600);
    const m = Math.floor((cd_remaining % 3600) / 60);
    const s = cd_remaining % 60;
    cdHtml = `
      <div class="boss-cd-banner" style="margin-bottom:12px">
        ⏳ Cooldown: <span id="boss-cd-countdown">${h}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s</span>
      </div>`;
    if (typeof _startBossCdCountdown === 'function') _startBossCdCountdown(cd_remaining);
  }

  container.innerHTML = `
    <div class="boss-encounter-wrap">
      <div class="boss-encounter-header">
        <button class="btn-back" onclick="loadDungeons()">← Mapa</button>
        <span class="boss-zone-label">${esc(dungeon_emoji)} ${esc(dungeon_name)}</span>
        <span class="boss-progress-badge">${highest_boss}/${total_bosses}</span>
      </div>
      ${cdHtml}
      <div class="boss-encounter-card">
        <div class="bec-floor">Floor ${esc(floorLabel)}</div>
        ${milestoneBadge}
        <div class="bec-icon">👹</div>
        <div class="bec-name">${esc(b.name)}</div>
        <div class="bec-desc">${esc(b.desc)}</div>
        <div class="bec-stats">
          <div class="bec-stat"><span class="bec-stat-val">${hp}</span><span class="bec-stat-lbl">HP</span></div>
          <div class="bec-stat"><span class="bec-stat-val">${atk}</span><span class="bec-stat-lbl">ATK</span></div>
          <div class="bec-stat"><span class="bec-stat-val">${def_}</span><span class="bec-stat-lbl">DEF</span></div>
          <div class="bec-stat"><span class="bec-stat-val">${spd}</span><span class="bec-stat-lbl">SPD</span></div>
        </div>
        <div class="bec-hp-bar-wrap">
          <div class="bec-hp-label">HP: <span>${hp}</span> / <span>${hp}</span></div>
          <div class="bec-hp-bar"><div class="bec-hp-fill" style="width:100%"></div></div>
        </div>
        <button class="bec-fight-btn ${on_cooldown ? 'disabled' : ''}"
                ${on_cooldown ? 'disabled' : `onclick="fightBoss('${dungeon_key}', ${b.num})"`}>
          ${on_cooldown ? '⏳ Cooldown' : '⚔️ Bojovat'}
        </button>
        <div class="bec-mult-note">Obtížnost ×${mult}</div>
      </div>
    </div>`;
}

// ── Boss fight ────────────────────────────────────────────────────────────────

async function fightBoss(dungeonKey, bossNum) {
  document.querySelectorAll('.boss-row.available').forEach(r => { r.onclick = null; });

  try {
    const data = await api('POST', '/dungeon/boss/fight', {
      dungeon_key: dungeonKey,
      boss_num:    bossNum,
    });

    if (data.result === 'victory') {
      const { rewards, boss_name } = data;
      let msg = `✅ ${esc(boss_name)} poražen! +${rewards.xp} XP, +${rewards.gold} 🪙`;
      if (rewards.item_drop) msg += ` | 🎁 ${esc(rewards.item_drop.name)} (${esc(rewards.item_drop.rarity)})`;
      toast(msg, 's', 5000);
      if (rewards.leveled_up) toast(`🎉 Level up! Nyní level ${rewards.new_level}!`, 's', 4000);
      const updatedChar = await api('GET', '/character/me');
      updateUI(updatedChar);
    } else {
      let msg;
      if (data.permadeath) {
        msg = `💀 ${esc(data.boss_name)} tě zabil! PERMADEATH!`;
      } else if (data.gold_lost > 0) {
        msg = `☠️ ${esc(data.boss_name)} tě porazil. Ztratil jsi ${data.gold_lost} 🪙`;
      } else {
        msg = `☠️ ${esc(data.boss_name)} tě porazil.`;
      }
      toast(msg, 'e', 5000);
      const updatedChar = await api('GET', '/character/me');
      updateUI(updatedChar);
    }

    _showBossCombatLog(data);

    if (data.permadeath) {
      setTimeout(() => location.reload(), 3000);
      return;
    }

    await openZoneBossView(dungeonKey);

  } catch (e) {
    toast(e.message || 'Chyba souboje.', 'e');
    await openZoneBossView(dungeonKey);
  }
}

function _showBossCombatLog(data) {
  if (typeof showCombatResult === 'function') {
    showCombatResult(data.combat_log, data.events, data.result === 'victory');
  }
}

// ── Cooldown countdown ────────────────────────────────────────────────────────

function _formatCd(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function _startBossCdCountdown(seconds) {
  if (_bossCdTimer) clearInterval(_bossCdTimer);
  let remaining = seconds;
  _bossCdTimer = setInterval(() => {
    remaining--;
    const el = document.getElementById('boss-cd-countdown');
    if (!el || remaining <= 0) {
      clearInterval(_bossCdTimer);
      if (remaining <= 0) loadDungeons();
      return;
    }
    const h = Math.floor(remaining / 3600);
    const m = Math.floor((remaining % 3600) / 60);
    const s = remaining % 60;
    el.textContent = `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
  }, 1000);
}
