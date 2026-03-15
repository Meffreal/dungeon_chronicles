/**
 * world_events.js — World Events systém (komunální sezónní cíle)
 */

let _weData = null;
let _weTimer = null;

async function loadWorldEvent() {
    const root = document.getElementById('we-root');
    if (!root) return;
    try {
        const d = await api('GET', '/world-events/current');
        _weData = d;
        renderWorldEvent(d, root);
    } catch(e) {
        root.innerHTML = `<div style="color:var(--accent);text-align:center;padding:40px">${esc(e.message)}</div>`;
    }
}

function renderWorldEvent(d, root) {
    if (!d.event) {
        root.innerHTML = `
            <div class="we-empty">
                <div class="we-empty-icon">🌍</div>
                <div class="we-empty-title">Žádný aktivní World Event</div>
                <div class="we-empty-sub">Brzy přijde nová výzva pro celou komunitu. Sleduj nástěnku!</div>
            </div>`;
        return;
    }

    const ev = d.event;
    _startWeCountdown(ev, root);

    // Progress bar
    const pct = ev.progress_pct;
    const progressColor = ev.is_completed ? 'var(--green2)' : (pct >= 75 ? 'var(--gold2)' : 'var(--accent2)');

    // Typ eventu ikona
    const typeIcons = {
        quests:         '📜',
        kills:          '⚔',
        dungeon_clears: '🏰',
        boss_damage:    '💀',
    };
    const typeIcon = typeIcons[ev.event_type] || '🌍';

    // Reward sekce
    const rewardHtml = `
        <div class="we-rewards">
            <div class="we-reward-chip"><span>💰</span> ${ev.reward_gold} G</div>
            ${ev.reward_crystals > 0 ? `<div class="we-reward-chip we-crystal-chip"><span>💎</span> ${ev.reward_crystals} Crystalů</div>` : ''}
            ${ev.reward_title ? `<div class="we-reward-chip we-title-chip"><span>🏷</span> "${esc(ev.reward_title)}"</div>` : ''}
        </div>`;

    // Claim tlačítko
    let actionHtml = '';
    if (ev.is_completed && d.can_claim) {
        actionHtml = `<button class="btn we-claim-btn" onclick="claimWorldEvent()">🎁 Vyzvednout odměnu</button>`;
    } else if (ev.is_completed && d.is_claimed) {
        actionHtml = `<div class="we-claimed-badge">✅ Odměna vybrána</div>`;
    } else if (ev.is_completed && !d.can_claim && !d.is_claimed) {
        actionHtml = `<div class="we-no-contrib">⚠️ Nepřispěl jsi k tomuto eventu — odměnu nelze vyzvednout.</div>`;
    }

    // Vlastní příspěvek
    const ownPct = ev.goal > 0 ? Math.min(100, Math.round(d.own_contribution / ev.goal * 100 * 10) / 10) : 0;
    const ownHtml = d.own_contribution > 0
        ? `<div class="we-own-contrib">Tvůj příspěvek: <strong>${d.own_contribution.toLocaleString('cs-CZ')}</strong> ${ev.event_type_label.toLowerCase()} (${ownPct}% cíle)</div>`
        : `<div class="we-own-contrib we-own-zero">Zatím jsi nepřispěl. Dokončuj ${ev.event_type_label.toLowerCase()}!</div>`;

    // Top přispěvatelé
    const topHtml = d.top_contributors.length
        ? d.top_contributors.map((c, i) => `
            <div class="we-contrib-row ${i === 0 ? 'we-contrib-first' : ''}">
                <span class="we-contrib-rank">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i+1}`}</span>
                <span class="we-contrib-name">${esc(c.name)}</span>
                <span class="we-contrib-val">${c.contribution.toLocaleString('cs-CZ')}</span>
            </div>`).join('')
        : `<div style="color:var(--text3);font-size:.78rem;font-style:italic">Zatím nikdo nepřispěl.</div>`;

    root.innerHTML = `
        <div class="we-header">
            <div class="we-event-badge">${ev.is_completed ? '✅ DOKONČENO' : '🔥 AKTIVNÍ'}</div>
            <div class="we-icon">${typeIcon}</div>
            <h2 class="we-title">${esc(ev.name)}</h2>
            <p class="we-desc">${esc(ev.description)}</p>
        </div>

        <div class="we-main-card">
            <!-- Timer -->
            <div class="we-timer-row">
                <span class="we-timer-label">${ev.is_completed ? 'Dokončeno!' : 'Zbývá'}</span>
                <span class="we-timer" id="we-countdown">${ev.is_completed ? '—' : _formatWeTime(ev.remaining_seconds)}</span>
                <span class="we-contribs">${d.contributor_count} přispěvatelů</span>
            </div>

            <!-- Progress bar -->
            <div class="we-progress-wrap">
                <div class="we-progress-labels">
                    <span class="we-prog-label">${ev.event_type_label}</span>
                    <span class="we-prog-nums">
                        <strong style="color:${progressColor}">${ev.current_progress.toLocaleString('cs-CZ')}</strong>
                        <span style="color:var(--text3)"> / ${ev.goal.toLocaleString('cs-CZ')}</span>
                    </span>
                </div>
                <div class="we-progress-track">
                    <div class="we-progress-fill ${ev.is_completed ? 'we-fill-done' : ''}" style="width:${pct}%;background:${progressColor}"></div>
                    <div class="we-progress-pct">${pct}%</div>
                </div>
            </div>

            ${ownHtml}

            <!-- Odměny -->
            <div class="we-rewards-section">
                <div class="we-section-label">Odměna za dokončení</div>
                ${rewardHtml}
                <div class="we-reward-note">Proporcionální gold dle příspěvku · Crystaly + titul dostane každý přispěvatel</div>
            </div>

            ${actionHtml}
        </div>

        <!-- Top přispěvatelé -->
        <div class="we-leaderboard">
            <div class="we-section-label">Top přispěvatelé</div>
            <div class="we-contrib-list">${topHtml}</div>
        </div>
    `;
}

function _formatWeTime(secs) {
    if (secs <= 0) return '0s';
    const d = Math.floor(secs / 86400);
    const h = Math.floor((secs % 86400) / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m ${s}s`;
}

function _startWeCountdown(ev, root) {
    if (_weTimer) clearInterval(_weTimer);
    if (ev.is_completed || ev.remaining_seconds <= 0) return;

    let remaining = ev.remaining_seconds;
    _weTimer = setInterval(() => {
        remaining--;
        const el = document.getElementById('we-countdown');
        if (!el) { clearInterval(_weTimer); return; }
        if (remaining <= 0) {
            clearInterval(_weTimer);
            el.textContent = 'Vypršel';
            loadWorldEvent();
            return;
        }
        el.textContent = _formatWeTime(remaining);
    }, 1000);
}

async function claimWorldEvent() {
    try {
        const d = await api('POST', '/world-events/claim');
        toast(d.message || '🎁 Odměna vybrána!', 's', 5000);
        if (d.awarded_title) toast(`Nový titul: "${d.awarded_title}"`, 'i', 4000);
        await loadWorldEvent();
    } catch(e) {
        toast(e.message || 'Chyba při vyzvednutí odměny.', 'e');
    }
}
