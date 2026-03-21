// ══════════════════════════════════════════════════════════════════════════════
// COMBAT ANIMATION SYSTEM v2.0
// Řídí vizuální replay combat logu z backendu.
//
// Podporuje dva formáty:
//   1. Structured events:  showCombatReplay(events, ...) — events je list[CombatEvent dict]
//   2. Text log (compat):  showCombatReplay(log, ...)    — log je list[string]
//
// Frontend NIKDY nepočítá combat — pouze přehrává backend výsledek.
// ══════════════════════════════════════════════════════════════════════════════

// ── Konstanty ─────────────────────────────────────────────────────────────────
const CR_EVENT_DELAY    = 490;   // ms mezi eventy
const CR_ROUND_DELAY    = 360;   // extra delay před novým kolem
const CR_PHASE_DELAY    = 1300;  // extra delay při phase change
const CR_STATUS_DELAY   = 220;   // delay pro status ticky (rychlé)
const CR_ABILITY_DELAY  = 700;   // delay pro ability efekty
const CR_RESULT_DELAY   = 1000;  // delay před zobrazením výsledku

// Event typy (musí odpovídat backendu)
const EVT_ATTACK       = "attack";
const EVT_CRIT         = "crit";
const EVT_DODGE        = "dodge";
const EVT_ABILITY      = "ability";
const EVT_STATUS_APPLY = "status_apply";
const EVT_STATUS_TICK  = "status_tick";
const EVT_STATUS_EXPIRE= "status_expire";
const EVT_PHASE_CHANGE = "phase_change";
const EVT_HEAL         = "heal";
const EVT_ROUND_START  = "round_start";
const EVT_COMBAT_END   = "combat_end";

// Barvy status efektů
const STATUS_COLORS = {
  bleed:  "#e74c3c",
  poison: "#2ecc71",
  stun:   "#f39c12",
  shield: "#3498db",
  burn:   "#e67e22",
  weaken: "#9b59b6",
  slow:   "#1abc9c",
  regen:  "#27ae60",
};

let _crTimer     = null;
let _crSoundCtx  = null;

// ── Sound System ───────────────────────────────────────────────────────────────
function _getSoundCtx() {
  if (!_crSoundCtx) {
    try { _crSoundCtx = new (window.AudioContext || window.webkitAudioContext)(); }
    catch(e) { return null; }
  }
  return _crSoundCtx;
}

function playSound(type) {
  const ctx = _getSoundCtx();
  if (!ctx) return;

  const osc  = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);

  const sounds = {
    hit:     { freq: 180, dur: 0.08, type: 'square',   vol: 0.15 },
    crit:    { freq: 420, dur: 0.18, type: 'sawtooth',  vol: 0.25 },
    dodge:   { freq: 900, dur: 0.06, type: 'sine',      vol: 0.10 },
    ability: { freq: 240, dur: 0.28, type: 'sawtooth',  vol: 0.22 },
    phase:   { freq: 80,  dur: 0.60, type: 'square',    vol: 0.35 },
    victory: { freq: 520, dur: 0.45, type: 'sine',      vol: 0.30 },
    defeat:  { freq: 110, dur: 0.70, type: 'triangle',  vol: 0.20 },
    status:  { freq: 320, dur: 0.10, type: 'sine',      vol: 0.12 },
    heal:    { freq: 660, dur: 0.15, type: 'sine',      vol: 0.15 },
  };
  const s = sounds[type] || sounds.hit;

  osc.type              = s.type;
  osc.frequency.value   = s.freq;
  gain.gain.setValueAtTime(s.vol, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + s.dur);

  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + s.dur);
}

// ── DiceBear Avatar helper ──────────────────────────────────────────────────
function _buildAvatarImg(appearance, side) {
  if (typeof buildAvatarUrl === 'function' && appearance) {
    const url = buildAvatarUrl(appearance);
    return `<img class="cr-avatar-img" src="${url}" alt="avatar" loading="lazy">`;
  }
  return `<div class="cr-avatar-placeholder">${side === 'player' ? '⚔' : '👾'}</div>`;
}

// ── Hlavní funkce ──────────────────────────────────────────────────────────────

/**
 * Spustí combat replay animaci.
 *
 * @param {Array}    logOrEvents   — list[string] NEBO list[CombatEvent dict]
 * @param {string}   playerName
 * @param {string}   enemyName
 * @param {boolean}  won           — Vyhrál hráč?
 * @param {number}   playerHpMax
 * @param {number}   enemyHpMax
 * @param {Object}   opts          — volitelné: { playerAppearance, isBoss, bossEmoji, title, rewards }
 */
function showCombatReplay(logOrEvents, playerName, enemyName, won,
                           playerHpMax, enemyHpMax, opts = {}) {
  // Cleanup
  if (_crTimer) { clearTimeout(_crTimer); _crTimer = null; }
  document.getElementById('combat-replay-overlay')?.remove();

  // Detekce formátu
  const isStructured = Array.isArray(logOrEvents)
    && logOrEvents.length > 0
    && typeof logOrEvents[0] === 'object'
    && logOrEvents[0].type !== undefined;

  const overlay = _buildOverlay(playerName, enemyName, playerHpMax, enemyHpMax, opts);
  document.body.appendChild(overlay);
  requestAnimationFrame(() => overlay.classList.add('cr-open'));

  if (isStructured) {
    _animateEvents(logOrEvents, playerName, enemyName, won, playerHpMax, enemyHpMax, opts);
  } else {
    _animateTextLog(logOrEvents, playerName, enemyName, won, playerHpMax, enemyHpMax);
  }
}

// ── Sestavení overlay HTML ─────────────────────────────────────────────────────

function _buildOverlay(playerName, enemyName, playerHpMax, enemyHpMax, opts) {
  const overlay = document.createElement('div');
  overlay.id        = 'combat-replay-overlay';
  overlay.className = 'cr-overlay';

  const playerAvatar = _buildAvatarImg(opts.playerAppearance, 'player');
  const enemyAvatar  = opts.enemyAppearance
    ? _buildAvatarImg(opts.enemyAppearance, 'enemy')
    : `<div class="cr-enemy-emoji">${opts.bossEmoji || (opts.isBoss ? '👾' : '⚔')}</div>`;
  const title        = opts.title || (opts.isBoss ? '⚔ Boss Combat' : '⚔ Combat Replay');

  const vsSvg = `<svg class="cr-vs-svg" viewBox="0 0 32 40" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="crBlade" x1="13" y1="2" x2="19" y2="2" gradientUnits="userSpaceOnUse"><stop stop-color="#5a4a38"/><stop offset="0.45" stop-color="#c4a882"/><stop offset="1" stop-color="#3a2a20"/></linearGradient></defs><path d="M15 2 L16 1 L17 2" fill="#c4a882" stroke="#c4a882" stroke-width="0.5"/><path d="M14.5 2 L15.5 2 L16.5 22 L16 24 L15.5 22 L16.5 2 L17.5 2 Z" fill="url(#crBlade)" stroke="#8a7060" stroke-width="0.5"/><line x1="16" y1="3" x2="16" y2="20" stroke="#1a1010" stroke-width="0.5" opacity="0.7"/><path d="M6 22 Q10 20.5 16 22 Q22 20.5 26 22 L25.5 24.5 Q19 23 16 23 Q13 23 6.5 24.5 Z" fill="#221814" stroke="#7a6a5a" stroke-width="0.9"/><path d="M6 22 Q4 23 4.5 24.5 Q6 25.5 6.5 24.5" fill="#221814" stroke="#b89a6a" stroke-width="0.7"/><path d="M26 22 Q28 23 27.5 24.5 Q26 25.5 25.5 24.5" fill="#221814" stroke="#b89a6a" stroke-width="0.7"/><path d="M16 23 L17 24.5 L16 26 L15 24.5 Z" fill="#0f0808" stroke="#b89a6a" stroke-width="0.7"/><path d="M16 23 L16.8 24.5 L16 25.5 L15.2 24.5 Z" fill="#7a2020" opacity="0.9"/><rect x="15.2" y="26" width="1.6" height="5" rx="0.5" fill="#2a1808" stroke="#6a3a18" stroke-width="0.7"/><path d="M14 31 Q16 33 18 31 L17.5 31 Q16 32.5 14.5 31 Z" fill="#221814" stroke="#7a6a5a" stroke-width="0.9"/><circle cx="16" cy="31" r="1" fill="#7a2020" stroke="#b89a6a" stroke-width="0.4"/></svg>`;

  overlay.innerHTML = `
    <div class="cr-modal ${opts.isBoss ? 'cr-modal-boss' : ''}">
      <div class="cr-corner cr-corner-tl"></div>
      <div class="cr-corner cr-corner-tr"></div>
      <div class="cr-corner cr-corner-bl"></div>
      <div class="cr-corner cr-corner-br"></div>

      <div class="cr-header">
        <span class="cr-title">${esc(title)}</span>
        <button class="cr-close" onclick="closeCombatReplay()">✕ Přeskočit</button>
      </div>

      <!-- Combatants -->
      <div class="cr-combatants">
        <div class="cr-side cr-player">
          <div class="cr-avatar" id="cr-avatar-p">${playerAvatar}</div>
          <div class="cr-name">${esc(playerName)}</div>
          <div class="cr-statuses" id="cr-statuses-p"></div>
          <div class="cr-hp-wrap">
            <div class="cr-hp-track">
              <div class="cr-hp-fill cr-hp-p" id="cr-hp-p" style="width:100%"></div>
            </div>
            <div class="cr-hp-label" id="cr-hp-p-lbl">${playerHpMax} / ${playerHpMax}</div>
          </div>
          <div class="cr-dmg-anchor" id="cr-dmg-p"></div>
        </div>

        <div class="cr-vs-block">
          <div class="cr-vs-icon" id="cr-vs-icon">${vsSvg}</div>
          <div class="cr-round-badge" id="cr-round-badge">Kolo 1</div>
          <div class="cr-phase-indicator" id="cr-phase-indicator" style="display:none"></div>
        </div>

        <div class="cr-side cr-enemy">
          <div class="cr-avatar cr-avatar-enemy" id="cr-avatar-e">
            ${enemyAvatar}
          </div>
          <div class="cr-name">${esc(enemyName)}</div>
          <div class="cr-statuses" id="cr-statuses-e"></div>
          <div class="cr-hp-wrap">
            <div class="cr-hp-track">
              <div class="cr-hp-fill cr-hp-e" id="cr-hp-e" style="width:100%"></div>
            </div>
            <div class="cr-hp-label" id="cr-hp-e-lbl">${enemyHpMax} / ${enemyHpMax}</div>
          </div>
          <div class="cr-dmg-anchor" id="cr-dmg-e"></div>
        </div>
      </div>

      <!-- Log -->
      <div class="cr-log" id="cr-log"></div>

      <!-- Result (hidden) -->
      <div class="cr-result" id="cr-result" style="display:none">
        <div class="cr-result-ico" id="cr-result-ico"></div>
        <div class="cr-result-txt" id="cr-result-txt"></div>
        <div class="cr-result-rewards" id="cr-result-rewards"></div>
        <button class="btn btn-gold" onclick="closeCombatReplay()">Zavřít</button>
      </div>
    </div>
  `;
  return overlay;
}

// ── Structured events animace ──────────────────────────────────────────────────

function _animateEvents(events, playerName, enemyName, won,
                         playerHpMax, enemyHpMax, opts) {
  let idx   = 0;
  let pHp   = playerHpMax;
  let eHp   = enemyHpMax;
  let round = 0;

  const activeStatuses = { player: {}, enemy: {} };

  function processNext() {
    if (idx >= events.length) {
      setTimeout(() => _showResult(won, playerName, opts.rewards), CR_RESULT_DELAY);
      return;
    }

    const evt    = events[idx++];
    const isActorPlayer = (evt.actor === playerName);
    let   delay  = CR_EVENT_DELAY;

    switch (evt.type) {
      case EVT_ROUND_START:
        round = evt.round;
        _updateRoundBadge(round);
        _appendLogRow(evt.text, 'cr-round-hdr');
        delay = CR_ROUND_DELAY;
        break;

      case EVT_ATTACK:
        _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax);
        _appendLogRow(evt.text, 'cr-attack');
        _spawnFloat(isActorPlayer ? 'cr-dmg-e' : 'cr-dmg-p', evt.damage, false, false);
        _shakeAvatar(isActorPlayer ? 'cr-avatar-e' : 'cr-avatar-p', 'light');
        playSound('hit');
        break;

      case EVT_CRIT:
        _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax);
        _appendLogRow(evt.text, 'cr-crit');
        _spawnFloat(isActorPlayer ? 'cr-dmg-e' : 'cr-dmg-p', evt.damage, true, false);
        _shakeAvatar(isActorPlayer ? 'cr-avatar-e' : 'cr-avatar-p', 'heavy');
        _flashScreen('cr-flash-crit');
        playSound('crit');
        delay = CR_EVENT_DELAY + 80;
        break;

      case EVT_DODGE:
        _appendLogRow(evt.text, 'cr-dodge');
        _shakeAvatar(isActorPlayer ? 'cr-avatar-p' : 'cr-avatar-e', 'dodge');
        playSound('dodge');
        delay = CR_EVENT_DELAY - 60;
        break;

      case EVT_ABILITY: {
        _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax);
        const cls = 'cr-ability cr-ability-' + (isActorPlayer ? 'player' : 'enemy');
        _appendLogRow(evt.text, cls);
        _spawnFloat(isActorPlayer ? 'cr-dmg-e' : 'cr-dmg-p', evt.damage, evt.is_crit, true);
        _shakeAvatar(isActorPlayer ? 'cr-avatar-e' : 'cr-avatar-p', 'heavy');
        _flashAbilityOverlay(evt.ability_emoji);
        playSound('ability');
        delay = CR_ABILITY_DELAY;
        break;
      }

      case EVT_STATUS_APPLY: {
        const side = isActorPlayer ? 'enemy' : 'player';
        _addStatusIcon(side, evt.status_name, evt.status_emoji);
        if (evt.text) _appendLogRow(evt.text, 'cr-status-apply');
        playSound('status');
        delay = CR_STATUS_DELAY;
        break;
      }

      case EVT_STATUS_TICK: {
        const side = (evt.target === playerName) ? 'player' : 'enemy';
        if (evt.damage > 0) {
          _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax);
          _spawnFloat(side === 'player' ? 'cr-dmg-p' : 'cr-dmg-e',
                      evt.damage, false, false, evt.status_emoji);
        }
        if (evt.text) _appendLogRow(evt.text, 'cr-status-tick');
        delay = CR_STATUS_DELAY;
        break;
      }

      case EVT_STATUS_EXPIRE: {
        const side = (evt.actor === playerName) ? 'player' : 'enemy';
        _removeStatusIcon(side, evt.status_name);
        if (evt.text) _appendLogRow(evt.text, 'cr-status-expire');
        delay = CR_STATUS_DELAY;
        break;
      }

      case EVT_HEAL: {
        const side = (evt.actor === playerName) ? 'player' : 'enemy';
        _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax);
        _spawnFloat(side === 'player' ? 'cr-dmg-p' : 'cr-dmg-e',
                    evt.heal, false, false, '💚', true);
        if (evt.text) _appendLogRow(evt.text, 'cr-heal');
        playSound('heal');
        delay = CR_STATUS_DELAY;
        break;
      }

      case EVT_PHASE_CHANGE:
        _triggerPhaseChange(evt);
        _appendLogRow(evt.text, 'cr-phase-change');
        playSound('phase');
        delay = CR_PHASE_DELAY;
        break;

      case EVT_COMBAT_END:
        _appendLogRow(evt.text, won ? 'cr-win' : 'cr-lose');
        delay = CR_RESULT_DELAY;
        // showResult se zavolá po delay — skip setTimeout níže
        _crTimer = setTimeout(() => _showResult(won, playerName, opts.rewards), delay);
        return;

      default:
        // Fallback — zobraz jako prostý log řádek
        if (evt.text) _appendLogRow(evt.text, '');
    }

    _crTimer = setTimeout(processNext, delay);
  }

  processNext();
}

// ── Text log animace (backward compat) ────────────────────────────────────────

function _animateTextLog(log, playerName, enemyName, won, playerHpMax, enemyHpMax) {
  let pHp    = playerHpMax;
  let eHp    = enemyHpMax;
  let lineIdx = 0;

  function parseHp(line) {
    const pm = line.match(new RegExp(escapeRegex(playerName) + '\\s+HP:\\s*(\\d+)'));
    const em = line.match(new RegExp(escapeRegex(enemyName)  + '\\s+HP:\\s*(\\d+)'));
    if (pm) pHp = parseInt(pm[1]);
    if (em) eHp = parseInt(em[1]);
  }

  function nextLine() {
    if (lineIdx >= log.length) {
      setTimeout(() => _showResult(won, playerName, null), CR_RESULT_DELAY);
      return;
    }
    const line  = log[lineIdx++];
    const extra = line.startsWith('[Kolo') ? CR_ROUND_DELAY : 0;

    parseHp(line);

    // Sestav CSS třídu
    let cls = '';
    if (line.startsWith('[Kolo'))                                          cls = 'cr-round-hdr';
    else if (line.includes('použil') && (line.includes('🪨')||line.includes('🔥')||line.includes('🎯'))) {
      cls = 'cr-ability cr-ability-player';
      if (line.includes('🔥')) cls += ' cr-mage';
      else if (line.includes('🪨')) cls += ' cr-warrior';
      else if (line.includes('🎯')) cls += ' cr-ranger';
    }
    else if (line.includes('KRITICKÝ'))                                     cls = 'cr-crit';
    else if (line.includes('uhnul') || line.includes('uhýbá'))             cls = 'cr-dodge';
    else if (line.includes('útočí') || line.includes('zasahuje'))          cls = 'cr-attack';
    else if (line.includes('trpí') || line.includes('⭐') || line.includes('🩸') || line.includes('☠️')) cls = 'cr-status-tick';
    else if (line.includes('zvítězil') || line.includes('vítěz'))          cls = 'cr-win';
    else if (line.includes('poražen'))                                      cls = 'cr-lose';
    else if (line.includes('⚡'))                                            cls = 'cr-phase-change';

    _appendLogRow(line, cls);

    // Update HP bars
    const pFill = document.getElementById('cr-hp-p');
    const eFill = document.getElementById('cr-hp-e');
    const pLbl  = document.getElementById('cr-hp-p-lbl');
    const eLbl  = document.getElementById('cr-hp-e-lbl');
    if (pFill) pFill.style.width = `${Math.max(0, pHp / playerHpMax * 100)}%`;
    if (eFill) eFill.style.width = `${Math.max(0, eHp / enemyHpMax * 100)}%`;
    if (pLbl)  pLbl.textContent  = `${pHp} / ${playerHpMax}`;
    if (eLbl)  eLbl.textContent  = `${eHp} / ${enemyHpMax}`;

    // Floating damage
    const dmgM = line.match(/→\s*(\d+)\s*dmg/);
    if (dmgM) {
      const isPlayer = line.includes(playerName + ' útočí') || line.includes(playerName + ' použil');
      const isCr     = line.includes('KRITICKÝ');
      _spawnFloat(isPlayer ? 'cr-dmg-e' : 'cr-dmg-p', parseInt(dmgM[1]), isCr, line.includes('použil'));
    }

    // Zvuky
    if (line.includes('KRITICKÝ'))        playSound('crit');
    else if (line.includes('použil'))     playSound('ability');
    else if (line.includes('uhnul'))      playSound('dodge');
    else if (line.includes('útočí') || line.includes('zasahuje')) playSound('hit');

    _crTimer = setTimeout(nextLine, CR_EVENT_DELAY + extra);
  }

  nextLine();
}

// ── Pomocné funkce ─────────────────────────────────────────────────────────────

function _appendLogRow(text, cssClass) {
  const logEl = document.getElementById('cr-log');
  if (!logEl || !text) return;

  const row = document.createElement('div');
  row.className = 'cr-log-row ' + cssClass;
  row.textContent = text;
  logEl.appendChild(row);
  logEl.scrollTop = logEl.scrollHeight;
}

function _updateHpBars(evt, playerName, enemyName, playerHpMax, enemyHpMax) {
  // Rozhodne která strana je player / enemy a aktualizuje HP bary
  const pFill = document.getElementById('cr-hp-p');
  const eFill = document.getElementById('cr-hp-e');
  const pLbl  = document.getElementById('cr-hp-p-lbl');
  const eLbl  = document.getElementById('cr-hp-e-lbl');

  // Použij target_hp pro obě strany
  let newPHp = null;
  let newEHp = null;

  if (evt.actor === playerName) {
    // Hráč útočil → target je nepřítel
    newEHp = evt.target_hp;
    newPHp = evt.actor_hp;
  } else {
    // Nepřítel útočil → target je hráč
    newPHp = evt.target_hp;
    newEHp = evt.actor_hp;
  }

  if (newPHp !== null && pFill && pLbl) {
    pFill.style.width = `${Math.max(0, newPHp / playerHpMax * 100)}%`;
    pLbl.textContent  = `${newPHp} / ${playerHpMax}`;
    if (newPHp / playerHpMax < 0.3) pFill.classList.add('cr-hp-critical');
    else pFill.classList.remove('cr-hp-critical');
  }
  if (newEHp !== null && eFill && eLbl) {
    const eMax = evt.target_hp_max || evt.actor_hp_max || enemyHpMax;
    eFill.style.width = `${Math.max(0, newEHp / (eMax || enemyHpMax) * 100)}%`;
    eLbl.textContent  = `${newEHp} / ${eMax || enemyHpMax}`;
    if (newEHp / (eMax || enemyHpMax) < 0.3) eFill.classList.add('cr-hp-critical');
    else eFill.classList.remove('cr-hp-critical');
  }
}

function _spawnFloat(anchorId, value, isCrit, isAbility, emoji = '', isHeal = false) {
  const anchor = document.getElementById(anchorId);
  if (!anchor) return;

  const el = document.createElement('div');
  let cls  = 'cr-float-dmg';
  if (isCrit)    cls += ' cr-float-crit';
  if (isAbility) cls += ' cr-float-ability';
  if (isHeal)    cls += ' cr-float-heal';
  el.className  = cls;
  el.textContent = isHeal
    ? `${emoji}+${value}`
    : (isCrit ? `💥 ${value}!` : `${emoji}-${value}`);
  anchor.appendChild(el);
  el.addEventListener('animationend', () => el.remove());
}

function _shakeAvatar(avatarId, intensity) {
  const el = document.getElementById(avatarId);
  if (!el) return;
  el.classList.remove('cr-shake-light', 'cr-shake-heavy', 'cr-shake-dodge');
  void el.offsetWidth; // reflow
  el.classList.add(`cr-shake-${intensity}`);
  el.addEventListener('animationend', () => {
    el.classList.remove('cr-shake-light', 'cr-shake-heavy', 'cr-shake-dodge');
  }, { once: true });
}

function _flashScreen(cls) {
  const overlay = document.getElementById('combat-replay-overlay');
  if (!overlay) return;
  overlay.classList.add(cls);
  setTimeout(() => overlay.classList.remove(cls), 200);
}

function _flashAbilityOverlay(emoji) {
  const modal = document.querySelector('.cr-modal');
  if (!modal) return;
  const flash = document.createElement('div');
  flash.className  = 'cr-ability-flash';
  flash.textContent = emoji || '✨';
  modal.appendChild(flash);
  flash.addEventListener('animationend', () => flash.remove());
}

function _updateRoundBadge(round) {
  const el = document.getElementById('cr-round-badge');
  if (el) el.textContent = `Kolo ${round}`;
}

function _addStatusIcon(side, statusName, emoji) {
  const containerId = side === 'player' ? 'cr-statuses-p' : 'cr-statuses-e';
  const container   = document.getElementById(containerId);
  if (!container) return;
  if (container.querySelector(`[data-status="${statusName}"]`)) return;

  const icon = document.createElement('span');
  icon.className        = 'cr-status-icon';
  icon.dataset.status   = statusName;
  icon.textContent      = emoji || '⚡';
  icon.title            = statusName;
  icon.style.borderColor = STATUS_COLORS[statusName] || '#888';
  container.appendChild(icon);
}

function _removeStatusIcon(side, statusName) {
  const containerId = side === 'player' ? 'cr-statuses-p' : 'cr-statuses-e';
  const container   = document.getElementById(containerId);
  if (!container) return;
  const icon = container.querySelector(`[data-status="${statusName}"]`);
  if (icon) {
    icon.classList.add('cr-status-expire-anim');
    icon.addEventListener('animationend', () => icon.remove(), { once: true });
  }
}

function _triggerPhaseChange(evt) {
  // Flash celého combatants bloku
  const combatants = document.querySelector('.cr-combatants');
  if (combatants) {
    combatants.classList.add('cr-phase-flash');
    setTimeout(() => combatants.classList.remove('cr-phase-flash'), 600);
  }

  // Zobraz phase indicator
  const phaseEl = document.getElementById('cr-phase-indicator');
  if (phaseEl) {
    phaseEl.style.display = 'block';
    phaseEl.textContent   = `⚡ FÁZE ${evt.phase_num}`;
    phaseEl.className     = 'cr-phase-indicator cr-phase-active';
  }

  // Enemy avatar shake
  _shakeAvatar('cr-avatar-e', 'heavy');

  // Světelný záblesk
  _flashScreen('cr-flash-phase');
}

function _showResult(won, playerName, rewards) {
  const resultEl = document.getElementById('cr-result');
  const icoEl    = document.getElementById('cr-result-ico');
  const txtEl    = document.getElementById('cr-result-txt');
  const rewEl    = document.getElementById('cr-result-rewards');
  if (!resultEl) return;

  icoEl.textContent = won ? '🏆' : '💀';
  txtEl.textContent = won ? `${playerName} zvítězil!` : `${playerName} byl poražen!`;
  resultEl.className = 'cr-result ' + (won ? 'cr-result-win' : 'cr-result-lose');
  resultEl.style.display = 'flex';

  if (rewards && rewEl) {
    const parts = [];
    if (rewards.xp)   parts.push(`+${rewards.xp} XP`);
    if (rewards.gold) parts.push(`+${rewards.gold} G`);
    if (rewards.item) parts.push(`🗡 ${rewards.item}`);
    rewEl.textContent = parts.join('  •  ');
  }

  playSound(won ? 'victory' : 'defeat');
}

// ── Public API ─────────────────────────────────────────────────────────────────

function closeCombatReplay() {
  if (_crTimer) { clearTimeout(_crTimer); _crTimer = null; }
  const overlay = document.getElementById('combat-replay-overlay');
  if (overlay) {
    overlay.classList.remove('cr-open');
    setTimeout(() => overlay.remove(), 300);
  }
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ── Combat Insights ────────────────────────────────────────────────────────────

/**
 * Analyzuje structured events a vrátí statistiky souboje.
 * Pracuje pouze na frontendových datech — žádný backend call.
 */
function analyzeCombatEvents(events, playerName) {
  if (!events || !events.length) return null;

  const analysis = {
    totalRounds:      0,
    playerTotalDamage: 0,
    enemyTotalDamage:  0,
    decisiveRound:    null,
    topAbility:       null,
    topAbilityDamage: 0,
    topAbilityCount:  0,
    keyStatus:        null,
    keyStatusDamage:  0,
    critCount:        0,
    dodgeCount:       0,
    abilityCount:     0,
    playerFinalHpPct: 100,
    enemyFinalHpPct:  100,
  };

  const abilityDmg  = {};   // name → total damage
  const abilityCnt  = {};   // name → triggers
  const statusDmg   = {};   // status → damage dealt to enemy

  let pHpMax = null, eHpMax = null;
  let pHpLast = null, eHpLast = null;

  for (const evt of events) {
    if (evt.type === EVT_ROUND_START) {
      analysis.totalRounds = Math.max(analysis.totalRounds, evt.round || 0);
      continue;
    }
    if (evt.type === EVT_COMBAT_END) continue;

    const isPA = evt.actor  === playerName;  // player is actor
    const isPT = evt.target === playerName;  // player is target

    // HP tracking
    if (isPA) {
      if (evt.actor_hp_max  !== undefined) pHpMax  = evt.actor_hp_max;
      if (evt.actor_hp      !== undefined) pHpLast = evt.actor_hp;
      if (evt.target_hp_max !== undefined) eHpMax  = evt.target_hp_max;
      if (evt.target_hp     !== undefined) eHpLast = evt.target_hp;
    } else if (isPT) {
      if (evt.target_hp_max !== undefined) pHpMax  = evt.target_hp_max;
      if (evt.target_hp     !== undefined) pHpLast = evt.target_hp;
      if (evt.actor_hp_max  !== undefined) eHpMax  = evt.actor_hp_max;
      if (evt.actor_hp      !== undefined) eHpLast = evt.actor_hp;
    }

    // Damage tracking
    if ((evt.type === EVT_ATTACK || evt.type === EVT_CRIT) && evt.damage > 0) {
      if (isPA) analysis.playerTotalDamage += evt.damage;
      else      analysis.enemyTotalDamage  += evt.damage;
    }

    // Ability damage (player)
    if (evt.type === EVT_ABILITY && evt.damage > 0 && isPA) {
      const n = evt.ability_name || '?';
      abilityDmg[n] = (abilityDmg[n] || 0) + evt.damage;
      abilityCnt[n] = (abilityCnt[n] || 0) + 1;
      analysis.abilityCount++;
      analysis.playerTotalDamage += evt.damage;
    }

    // Status tick damage on enemy
    if (evt.type === EVT_STATUS_TICK && evt.damage > 0 && !isPT) {
      const sn = evt.status_name || '?';
      statusDmg[sn] = (statusDmg[sn] || 0) + evt.damage;
      analysis.playerTotalDamage += evt.damage;
    }

    // Crits (player) & dodges (player)
    if (evt.type === EVT_CRIT  && isPA)  analysis.critCount++;
    if (evt.type === EVT_DODGE && isPT)  analysis.dodgeCount++;

    // Decisive round — first time either HP drops below 30%
    if (!analysis.decisiveRound && evt.round) {
      const lowP = pHpMax && pHpLast !== null && pHpLast / pHpMax < 0.30;
      const lowE = eHpMax && eHpLast !== null && eHpLast / eHpMax < 0.30;
      if (lowP || lowE) analysis.decisiveRound = evt.round;
    }
  }

  // Top ability
  for (const [n, d] of Object.entries(abilityDmg)) {
    if (d > analysis.topAbilityDamage) {
      analysis.topAbility      = n;
      analysis.topAbilityDamage = d;
      analysis.topAbilityCount  = abilityCnt[n] || 1;
    }
  }

  // Key status
  for (const [n, d] of Object.entries(statusDmg)) {
    if (d > analysis.keyStatusDamage) {
      analysis.keyStatus       = n;
      analysis.keyStatusDamage = d;
    }
  }

  // Final HP pct
  if (pHpMax && pHpLast !== null) analysis.playerFinalHpPct = Math.max(0, Math.round(pHpLast / pHpMax * 100));
  if (eHpMax && eHpLast !== null) analysis.enemyFinalHpPct  = Math.max(0, Math.round(eHpLast / eHpMax * 100));

  return analysis;
}

function _generateCombatTip(analysis, won, playerClass, playerStrategy) {
  if (!analysis) return null;
  const cls   = (playerClass    || '').toLowerCase();
  const strat = (playerStrategy || '').toLowerCase();

  if (!won) {
    if (analysis.enemyTotalDamage > analysis.playerTotalDamage * 2 && strat !== 'defensive')
      return 'Nepřítel způsoboval výrazně více poškození. Zkus Defensive strategii pro větší odolnost.';
    if (analysis.critCount === 0 && cls === 'ranger')
      return 'Žádné krity. Ranger s talentem Eagle Eye získá +8% šanci na kritický hit.';
    if (cls === 'mage' && strat !== 'burst')
      return 'Mage s Burst strategií způsobí maximum poškození v prvních kolech — využij to!';
    if (cls === 'warrior' && analysis.abilityCount === 0)
      return 'Neaktivovala se žádná schopnost — zkontroluj, zda máš dost MP pro Berserk.';
    if (analysis.totalRounds >= 25)
      return 'Souboj přesáhl 25 kol. Vyšší ATK nebo Aggro strategie ho zkrátí.';
    if (analysis.playerFinalHpPct > 10)
      return 'Těsná prohra! Malý nárůst DEF nebo HP by příště mohl stačit.';
    return 'Prohráno. Zkontroluj svůj Combat Build a uprav strategii.';
  } else {
    const dmgTotal = analysis.playerTotalDamage;
    if (analysis.topAbility && analysis.topAbilityDamage > dmgTotal * 0.35) {
      const pct = Math.round(analysis.topAbilityDamage / dmgTotal * 100);
      return `Schopnost "${analysis.topAbility}" způsobila ${pct}% celkového poškození — výborná synergie buildu!`;
    }
    if (analysis.critCount >= 4)
      return `${analysis.critCount} kritických hitů v jednom souboji — impozantní!`;
    if (analysis.dodgeCount >= 2)
      return `${analysis.dodgeCount} úspěšná uhnutí — SPD build nebo Evasion talent funguje!`;
    if (analysis.keyStatus && analysis.keyStatusDamage > 30)
      return `Status "${analysis.keyStatus}" přidal ${analysis.keyStatusDamage} poškození navíc — status buildy mají potenciál!`;
    return 'Výhráno! Tvůj build fungoval správně.';
  }
}

/**
 * Zobrazí Combat Insights panel v daném kontejneru.
 * Funguje pouze se structured events — pro text log nic nezobrazí.
 *
 * @param {string}  containerId    — ID DOM elementu
 * @param {Array}   events         — structured events (list[CombatEvent dict])
 * @param {boolean} won            — vyhrál hráč?
 * @param {string}  playerName     — jméno hráče
 * @param {string}  playerClass    — třída (warrior/mage/ranger)
 * @param {string}  playerStrategy — strategie (balanced/aggro/defensive/burst)
 */
function showCombatInsights(containerId, events, won, playerName, playerClass, playerStrategy) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Pouze structured events
  if (!events || !Array.isArray(events) || !events.length ||
      typeof events[0] !== 'object' || !events[0].type) {
    container.innerHTML = '';
    return;
  }

  const a   = analyzeCombatEvents(events, playerName);
  if (!a)  { container.innerHTML = ''; return; }

  const tip = _generateCombatTip(a, won, playerClass, playerStrategy);

  const highlights = [];
  if (a.topAbility) {
    highlights.push(`<div class="ci-highlight ci-hl-ability">
      ⚡ <strong>${esc(a.topAbility)}</strong> — ${a.topAbilityDamage} poškození (${a.topAbilityCount}× aktivace)
    </div>`);
  }
  if (a.keyStatus) {
    highlights.push(`<div class="ci-highlight ci-hl-status">
      🩸 Status <strong>${esc(a.keyStatus)}</strong> — ${a.keyStatusDamage} poškození
    </div>`);
  }
  if (a.critCount > 0) {
    highlights.push(`<div class="ci-highlight ci-hl-crit">
      💥 ${a.critCount} kritický${a.critCount === 1 ? '' : a.critCount < 5 ? 'é' : 'ch'} hit${a.critCount === 1 ? '' : a.critCount < 5 ? 'y' : 'ů'}
    </div>`);
  }
  if (a.dodgeCount > 0) {
    highlights.push(`<div class="ci-highlight ci-hl-dodge">
      🌀 ${a.dodgeCount} uhnut${a.dodgeCount === 1 ? 'í' : 'í'}
    </div>`);
  }
  if (a.decisiveRound) {
    highlights.push(`<div class="ci-highlight ci-hl-round">
      ⚔ Zlomový moment: kolo ${a.decisiveRound}
    </div>`);
  }

  const dmgTotal = a.playerTotalDamage + a.enemyTotalDamage;
  const dmgShare = dmgTotal > 0 ? Math.round(a.playerTotalDamage / dmgTotal * 100) : 0;

  container.innerHTML = `
    <div class="ci-panel ${won ? 'ci-win' : 'ci-lose'}">
      <div class="ci-header">📊 Combat Insights</div>
      <div class="ci-stats-row">
        <div class="ci-stat">
          <div class="ci-stat-val ci-val-atk">${a.playerTotalDamage}</div>
          <div class="ci-stat-lbl">Uděleno</div>
        </div>
        <div class="ci-stat">
          <div class="ci-stat-val ci-val-def">${a.enemyTotalDamage}</div>
          <div class="ci-stat-lbl">Přijato</div>
        </div>
        <div class="ci-stat">
          <div class="ci-stat-val">${a.totalRounds}</div>
          <div class="ci-stat-lbl">Kola</div>
        </div>
        <div class="ci-stat">
          <div class="ci-stat-val ${dmgShare >= 50 ? 'ci-val-atk' : 'ci-val-def'}">${dmgShare}%</div>
          <div class="ci-stat-lbl">Damage podíl</div>
        </div>
      </div>
      ${highlights.length ? `<div class="ci-highlights">${highlights.join('')}</div>` : ''}
      ${tip ? `<div class="ci-tip">💡 ${esc(tip)}</div>` : ''}
    </div>`;
}
