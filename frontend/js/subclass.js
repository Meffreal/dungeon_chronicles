/**
 * subclass.js — Specializace postavy
 * Odemčení na level 10. Volba je trvalá.
 */

let _subclassData = null;

async function loadSubclass() {
    const d = await api('GET', '/character/subclasses');
    _subclassData = d;
    renderSubclassPage(d);
}

function renderSubclassPage(d) {
    const root = document.getElementById('subclass-root');
    if (!root) return;

    // Pokud je již specializace zvolena
    if (d.current_subclass) {
        root.innerHTML = _renderChosenSubclass(d);
        return;
    }

    // Pokud level < 10
    if (!d.can_choose) {
        const lvlNeeded = 10 - d.level;
        root.innerHTML = `
            <div class="sub-locked">
                <div class="sub-locked-icon">🔒</div>
                <h2>Specializace odemčena na level 10</h2>
                <p>Zbývá získat <strong>${lvlNeeded}</strong> úroveň${lvlNeeded === 1 ? '' : (lvlNeeded < 5 ? 'ě' : 'í')}.</p>
                <p class="sub-locked-hint">Specializace ti dá silné pasivní bonusy i novou combat schopnost.</p>
            </div>`;
        return;
    }

    // Výběr specializace
    const subclassCards = Object.values(d.subclasses)
        .map(s => _subclassChoiceCard(s))
        .join('');

    root.innerHTML = `
        <div class="sub-choose-header">
            <h2>Vyber svou specializaci</h2>
            <p class="sub-choose-hint">
                ⚠️ Volba je <strong>trvalá</strong> — nelze ji po výběru změnit.
                Zamysli se, která specializace ti vyhovuje.
            </p>
        </div>
        <div class="sub-cards-grid">
            ${subclassCards}
        </div>`;
}

function _statMultLabel(key, val) {
    const names = {
        atk_mult: 'ATK', def_mult: 'DEF', hp_mult: 'HP',
        mp_mult: 'MP', spd_mult: 'SPD', luck_mult: 'LUCK',
    };
    const label = names[key] || key;
    const pct = Math.round((val - 1) * 100);
    const sign = pct >= 0 ? '+' : '';
    const cls  = pct >= 0 ? 'sub-stat-pos' : 'sub-stat-neg';
    return `<span class="${cls}">${sign}${pct}% ${label}</span>`;
}

function _subclassChoiceCard(s) {
    const statHtml = Object.entries(s.stat_mults)
        .map(([k, v]) => _statMultLabel(k, v))
        .join('');
    return `
        <div class="sub-card" onclick="confirmChooseSubclass('${s.key}', '${s.name}')">
            <div class="sub-card-emoji">${s.emoji}</div>
            <div class="sub-card-name">${s.name}</div>
            <div class="sub-card-desc">${s.description}</div>
            <div class="sub-card-stats">${statHtml}</div>
            <div class="sub-card-flavor">"${s.flavor}"</div>
            <button class="sub-choose-btn" onclick="event.stopPropagation(); confirmChooseSubclass('${s.key}', '${s.name}')">
                Zvolit ${s.name}
            </button>
        </div>`;
}

function _renderChosenSubclass(d) {
    const s = d.subclasses[d.current_subclass];
    if (!s) {
        return `<div class="sub-chosen"><p>Specializace: <strong>${d.current_subclass}</strong></p></div>`;
    }
    const statHtml = Object.entries(s.stat_mults)
        .map(([k, v]) => _statMultLabel(k, v))
        .join('');

    // Načti info o ability ze SUBCLASS_ABILITIES na frontendu (nebo jen přes char data)
    return `
        <div class="sub-chosen">
            <div class="sub-chosen-badge">${s.emoji}</div>
            <h2 class="sub-chosen-name">${s.name}</h2>
            <p class="sub-chosen-desc">${s.description}</p>
            <div class="sub-chosen-flavor">"${s.flavor}"</div>
            <div class="sub-chosen-stats">
                <div class="sub-stats-label">Pasivní bonusy</div>
                <div class="sub-stats-row">${statHtml}</div>
            </div>
            <div class="sub-chosen-locked">
                🔒 Specializace je trvalá a nelze ji změnit.
            </div>
        </div>`;
}

async function confirmChooseSubclass(key, name) {
    const confirmed = confirm(`Opravdu chceš zvolit specializaci "${name}"?\n\nTato volba je TRVALÁ a nelze ji změnit.`);
    if (!confirmed) return;
    await chooseSubclass(key);
}

async function chooseSubclass(key) {
    try {
        const d = await api('POST', '/character/choose-subclass', { subclass: key });
        // Aktualizuj globální char
        if (typeof char !== 'undefined') {
            Object.assign(char, d);
        }
        updateUI(d);
        toast(`Specializace ${key} zvolena! Tvé statistiky byly aktualizovány.`, 's', 4000);
        // Znovu načti stránku specializace
        await loadSubclass();
    } catch (e) {
        toast(e.message || 'Chyba při výběru specializace.', 'e');
    }
}
