// ── TRANSMOG SYSTÉM ────────────────────────────────────────────────────────────
// Kosmetický vzhled vybavení — hráč může nastavit jiný item jako vizuální
// reprezentaci slotu. Stats se nemění, pouze ikona/jméno/rarity.

const SLOT_CZ_TM = {
  weapon: 'Zbraň', helmet: 'Helma', armor: 'Zbroj',
  gloves: 'Rukavice', boots: 'Boty', ring: 'Prsten', amulet: 'Amulet',
};

let _tmogModalSlot = null;  // slot otevřeného modalu

// ── Otevřít modal ──────────────────────────────────────────────────────────────

async function openTransmogModal(slot) {
  _tmogModalSlot = slot;

  const modal = document.getElementById('transmog-modal');
  if (!modal) return;

  const title   = modal.querySelector('.tmog-modal-title');
  const content = modal.querySelector('.tmog-modal-content');

  if (title) title.textContent = `🎨 Transmog — ${SLOT_CZ_TM[slot] || slot}`;
  if (content) content.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div></div>';

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  try {
    const data = await api('GET', `/transmog/options?slot=${encodeURIComponent(slot)}`);
    renderTransmogOptions(data, content);
  } catch (e) {
    if (content) content.innerHTML = `<div class="empty-state">⚠️ ${esc(e.message || 'Chyba načítání.')}</div>`;
  }
}

function closeTransmogModal() {
  const modal = document.getElementById('transmog-modal');
  if (modal) modal.classList.add('hidden');
  document.body.style.overflow = '';
  _tmogModalSlot = null;
}

// ── Render options ──────────────────────────────────────────────────────────────

function renderTransmogOptions(data, container) {
  if (!container) return;

  const { slot, options, current_transmog, cost } = data;
  const equippedItem = char?.equipment?.[slot];

  // Header — aktuální stav
  const currentHtml = current_transmog
    ? `<div class="tmog-current">
         <span class="tmog-current-label">Aktuální transmog:</span>
         <span class="tmog-current-item" style="color:${RARITY_COL[current_transmog.rarity]||'#9d9d9d'}">
           ${esc(current_transmog.icon)} ${esc(current_transmog.name)}
         </span>
         <button class="tmog-clear-btn" onclick="clearTransmog('${slot}')">✕ Odstranit</button>
       </div>`
    : `<div class="tmog-current tmog-current-none">Žádný transmog nastaven.</div>`;

  // Cena
  const costHtml = `<div class="tmog-cost-note">💰 Nastavení transmogu: <strong>${cost} G</strong> · Tvůj gold: <strong>${(char?.gold||0).toLocaleString('cs')} G</strong></div>`;

  // Grid itemů
  let gridHtml = '';
  if (!options || options.length === 0) {
    gridHtml = `<div class="empty-state">Žádné ${SLOT_CZ_TM[slot]||slot} itemy v inventáři.<br>Získej je z questů nebo obchodu.</div>`;
  } else {
    const cards = options.map(inv => {
      const item = inv.item;
      if (!item) return '';
      const rc   = RARITY_COL[item.rarity] || '#9d9d9d';
      const isCurrentTmog = current_transmog && current_transmog.id === item.id;
      const isEquipped    = inv.is_equipped;

      const badges = [
        isEquipped     ? '<span class="tmog-badge tmog-badge-eq">Nasazeno</span>' : '',
        isCurrentTmog  ? '<span class="tmog-badge tmog-badge-active">✓ Transmog</span>' : '',
        inv.upgrade_level > 0 ? `<span class="tmog-badge tmog-badge-upg">★${inv.upgrade_level}</span>` : '',
      ].filter(Boolean).join('');

      const bonusChips = Object.entries(item.bonuses || {})
        .filter(([,v]) => v > 0)
        .slice(0, 3)
        .map(([k,v]) => `<span class="tmog-bonus-chip">+${v} ${k.toUpperCase()}</span>`)
        .join('');

      return `
        <div class="tmog-item-card ${isCurrentTmog ? 'tmog-item-active' : ''}" style="--rc:${rc}"
             onclick="applyTransmog('${slot}', ${item.id})">
          <div class="tmog-item-icon" style="filter:drop-shadow(0 2px 8px ${rc}88)">${esc(item.icon)}</div>
          <div class="tmog-item-body">
            <div class="tmog-item-name" style="color:${rc}">${esc(item.name)}</div>
            ${badges ? `<div class="tmog-item-badges">${badges}</div>` : ''}
            ${bonusChips ? `<div class="tmog-item-bonuses">${bonusChips}</div>` : ''}
          </div>
          <div class="rarity-pip" style="background:${rc}"></div>
        </div>`;
    }).join('');

    gridHtml = `<div class="tmog-item-grid">${cards}</div>`;
  }

  container.innerHTML = currentHtml + costHtml + gridHtml;
}

// ── Akce ───────────────────────────────────────────────────────────────────────

async function applyTransmog(slot, itemId) {
  if (!slot || !itemId) return;

  // Optimistický feedback
  const cards = document.querySelectorAll('.tmog-item-card');
  cards.forEach(c => c.style.opacity = '0.5');

  try {
    const result = await api('POST', '/transmog/set', {
      slot,
      cosmetic_item_id: itemId,
    });

    toast(`🎨 Transmog nastaven: ${result.item_name} (−${result.gold_spent} G)`, 's', 4000);
    closeTransmogModal();

    // Aktualizuj char data a znovu vykresli equipment
    if (typeof loadCharacter === 'function') {
      await loadCharacter();
    } else if (typeof renderEquip === 'function') {
      renderEquip();
    }
  } catch (e) {
    toast(e.message || 'Nastavení transmogu selhalo.', 'e');
    cards.forEach(c => c.style.opacity = '');
  }
}

async function clearTransmog(slot) {
  try {
    await api('POST', '/transmog/clear', { slot });
    toast(`Transmog pro slot '${SLOT_CZ_TM[slot]||slot}' odstraněn.`, 'i');
    closeTransmogModal();

    if (typeof loadCharacter === 'function') {
      await loadCharacter();
    } else if (typeof renderEquip === 'function') {
      renderEquip();
    }
  } catch (e) {
    toast(e.message || 'Odstranění transmogu selhalo.', 'e');
  }
}

async function clearAllTransmogs() {
  if (!confirm('Opravdu chceš odebrat všechny transmoogy?')) return;
  try {
    const result = await api('POST', '/transmog/clear-all', {});
    toast(`Odstraněno ${result.cleared} transmogů.`, 'i');

    if (typeof loadCharacter === 'function') {
      await loadCharacter();
    } else if (typeof renderEquip === 'function') {
      renderEquip();
    }
  } catch (e) {
    toast(e.message || 'Chyba při odstraňování.', 'e');
  }
}

// ── Init — přidej modal do DOM ─────────────────────────────────────────────────

function initTransmogModal() {
  if (document.getElementById('transmog-modal')) return;

  const modal = document.createElement('div');
  modal.id = 'transmog-modal';
  modal.className = 'tmog-modal-overlay hidden';
  modal.innerHTML = `
    <div class="tmog-modal" onclick="event.stopPropagation()">
      <div class="tmog-modal-header">
        <h3 class="tmog-modal-title">🎨 Transmog</h3>
        <button class="tmog-modal-close" onclick="closeTransmogModal()">✕</button>
      </div>
      <div class="tmog-modal-content"></div>
    </div>`;
  modal.addEventListener('click', closeTransmogModal);
  document.body.appendChild(modal);
}

// Spusť init po načtení
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTransmogModal);
} else {
  initTransmogModal();
}
