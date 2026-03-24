/**
 * prestige.js — Prestige systém (post-level-cap)
 */

let _prestigeData = null;

async function loadPrestige() {
    const root = document.getElementById('prestige-root');
    if (!root) return;
    try {
        const d = await api('GET', '/prestige/info');
        _prestigeData = d;
        renderPrestige(d, root);
    } catch(e) {
        root.innerHTML = `<div style="color:var(--accent);text-align:center;padding:40px">${esc(e.message)}</div>`;
    }
}

function renderPrestige(d, root) {
    const pl = d.prestige_level;
    const isMax50 = d.level >= d.max_level;

    // Badge prestige levelu
    const plBadge = pl > 0
        ? `<div class="prs-badge"><span class="prs-star">✦</span> Prestige ${pl}</div>`
        : '';

    // Stav — aktuální bonusy
    const curBonusHtml = pl > 0 ? `
        <div class="prs-cur-bonus">
            <div class="prs-section-label">Aktuální permanentní bonusy (Prestige ${pl})</div>
            <div class="prs-bonus-row">
                ${_bonusChip('ATK', d.current_bonuses.atk_pct)}
                ${_bonusChip('DEF', d.current_bonuses.def_pct)}
                ${_bonusChip('HP', d.current_bonuses.hp_pct)}
                ${_bonusChip('MP', d.current_bonuses.mp_pct)}
            </div>
        </div>` : '';

    // Cap info banner (zobrazí se pokud je hráč na nebo nad power capem)
    const capBanner = d.is_power_capped ? `
        <div class="prs-cap-banner">
            <span class="prs-cap-icon">⚡</span>
            <div>
                <div class="prs-cap-title">Maximální power dosažen (Prestige ${d.power_cap})</div>
                <div class="prs-cap-sub">Bonusy ke statům jsou na maximu: ATK/DEF/HP +${d.power_cap * 3}% · MP +${d.power_cap * 2}%.<br>Další prestige přinese jen tituly a kosmetiku.</div>
            </div>
        </div>` : '';

    // Info o dalším prestige
    const nextBonusesHtml = d.is_power_capped
        ? `<div class="prs-cap-note">⛔ Bonusy ke statům jsou na maximu — žádný další power nárůst</div>`
        : `<div class="prs-bonus-row">
                ${_bonusChip('ATK', d.next_bonuses.atk_pct)}
                ${_bonusChip('DEF', d.next_bonuses.def_pct)}
                ${_bonusChip('HP', d.next_bonuses.hp_pct)}
                ${_bonusChip('MP', d.next_bonuses.mp_pct)}
           </div>`;

    const nextInfo = `
        <div class="prs-next-card">
            <div class="prs-next-title">${d.is_power_capped ? '✨' : '🌟'} Prestige ${pl + 1} — ${d.is_power_capped ? 'Kosmetické odměny' : 'Bonusy po dokončení'}</div>
            ${nextBonusesHtml}
            ${d.upcoming_title ? `<div class="prs-title-reward">🏷️ Nový titul: <strong>${esc(d.upcoming_title)}</strong></div>` : ''}
            ${d.upcoming_frame ? `<div class="prs-frame-reward">🖼️ Nový portrait frame: <span class="prs-frame-tag">${esc(d.upcoming_frame)}</span></div>` : ''}
            <div class="prs-crystal-reward">💎 Odměna: <strong>${d.crystal_reward} Crystalů</strong></div>
        </div>`;

    // Reset / zachováno
    const resetHtml = d.resets.map(r => `<li>❌ ${esc(r)}</li>`).join('');
    const keepHtml  = d.keeps.map(k => `<li>✅ ${esc(k)}</li>`).join('');

    // Podmínka / tlačítko
    const actionHtml = isMax50
        ? `<button class="btn prs-ascend-btn" onclick="confirmPrestige()">🌟 Provést Prestige → Reset na Lv.1</button>`
        : `<div class="prs-locked">
               <div>🔒 Prestige vyžaduje <strong>Level ${d.max_level}</strong></div>
               <div class="prs-locked-sub">Aktuální level: ${d.level} / ${d.max_level}</div>
               <div class="prs-xp-bar-wrap"><div class="prs-xp-bar" style="width:${Math.min(100, Math.round(d.level/d.max_level*100))}%"></div></div>
           </div>`;

    // Tituly tabulka
    const titlesHtml = Object.entries(d.titles).map(([lvl, title]) => `
        <div class="prs-title-row ${pl >= +lvl ? 'prs-title-done' : ''}">
            <span class="prs-title-pl">✦ ${lvl}</span>
            <span class="prs-title-name">${esc(title)}</span>
            <span class="prs-title-status">${pl >= +lvl ? '✅' : '🔒'}</span>
        </div>`).join('');

    // Historie
    const histHtml = d.history.length
        ? d.history.map(h => `
            <div class="prs-hist-row">
                <span class="prs-hist-pl">✦ ${h.prestige_level}</span>
                <span>${h.title ? esc(h.title) : '—'}</span>
                <span class="prs-hist-crystals">+${h.crystals} 💎</span>
                <span class="prs-hist-date">${new Date(h.at+'Z').toLocaleDateString('cs-CZ')}</span>
            </div>`).join('')
        : '<div style="color:var(--text3);font-size:.78rem">Zatím žádný prestige.</div>';

    root.innerHTML = `
        <div class="prs-header">
            ${plBadge}
            <h2 class="prs-title">Prestige Systém</h2>
            <p class="prs-subtitle">Dosáhni levelu ${d.max_level}, resetuj a získej trvalé bonusy (cap: Prestige ${d.power_cap}).</p>
        </div>

        ${capBanner}
        ${curBonusHtml}
        ${nextInfo}
        ${actionHtml}

        <div class="prs-two-col">
            <div class="prs-list-card">
                <div class="prs-section-label">Co se resetuje</div>
                <ul class="prs-list">${resetHtml}</ul>
            </div>
            <div class="prs-list-card">
                <div class="prs-section-label">Co zůstane</div>
                <ul class="prs-list">${keepHtml}</ul>
            </div>
        </div>

        <div class="prs-titles-section">
            <div class="prs-section-label">Tituly za Prestige</div>
            ${titlesHtml}
        </div>

        <div class="prs-history">
            <div class="prs-section-label">Tvoje Prestige history</div>
            ${histHtml}
        </div>`;
}

function _bonusChip(stat, pct) {
    const sign = pct > 0 ? '+' : '';
    return `<span class="prs-chip">${stat} ${sign}${pct}%</span>`;
}

async function confirmPrestige() {
    const ok = confirm(
        `⚠️ PRESTIGE — Nevratná akce!\n\n` +
        `Tvůj level se resetuje na 1 a ztratíš:\n` +
        `• Level a XP\n• Stat body\n• Primary stats (vrátí se na základ třídy)\n• Talenty (odemknou se znovu při levelování)\n• CELÝ inventář a vybavení\n\n` +
        `Zachováš: gold, guild, specializaci, arena rank, crystaly.\n\n` +
        `Odměna: +${_prestigeData?.crystal_reward ?? 150} Crystalů + permanentní bonusy ke statům.\n\n` +
        `Opravdu chceš provést Prestige?`
    );
    if (!ok) return;
    await doPrestige();
}

async function doPrestige() {
    try {
        const d = await api('POST', '/prestige/ascend');
        // Aktualizuj globální char
        if (typeof char !== 'undefined' && d.character) {
            Object.assign(char, d.character);
            updateUI(d.character);
        }
        toast(d.message || '🌟 Prestige dosaženo!', 's', 5000);
        if (d.awarded_title) {
            toast(`🏷️ Nový titul: "${d.awarded_title}"`, 'i', 4000);
        }
        if (d.awarded_frame) {
            toast(`🖼️ Nový portrait frame: ${d.awarded_frame}`, 'i', 4000);
        }
        await loadPrestige();
    } catch(e) {
        toast(e.message || 'Chyba při prestige.', 'e');
    }
}
