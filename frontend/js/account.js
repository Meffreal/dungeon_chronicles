/* account.js — Správa účtu: export dat, smazání, anonymizace */

async function loadAccount() {
  const root = document.getElementById('account-root');
  if (!root) return;
  root.innerHTML = '<div style="color:var(--text2);text-align:center;padding:40px">Načítám...</div>';

  try {
    const status = await api('GET', '/account/status');
    root.innerHTML = _renderAccount(status);
  } catch (e) {
    root.innerHTML = '<div class="empty-state">Chyba načítání účtu.</div>';
  }
}

function _renderAccount(s) {
  const deleteWarning = s.is_deleted
    ? `<div class="acc-alert acc-alert-warn">
        ⚠ Váš účet je označen ke smazání — bude trvale odstraněn <strong>${s.delete_after}</strong>.
        <button class="btn btn-sm" onclick="accountCancelDelete()">Zrušit smazání</button>
       </div>`
    : '';

  const anonWarning = s.anonymized
    ? '<div class="acc-alert acc-alert-info">ℹ Tento účet byl anonymizován. Osobní data byla odstraněna.</div>'
    : '';

  return `
<div class="page-hdr">⚙ Správa účtu</div>

${deleteWarning}
${anonWarning}

<div class="acc-grid">

  <!-- Přehled -->
  <div class="acc-card">
    <div class="acc-card-title">👤 Informace o účtu</div>
    <div class="acc-row"><span class="acc-lbl">Uživatelské jméno</span><span class="acc-val">${s.username}</span></div>
    <div class="acc-row"><span class="acc-lbl">Email</span><span class="acc-val">${s.email}</span></div>
    <div class="acc-row"><span class="acc-lbl">Účet vytvořen</span><span class="acc-val">${s.created_at ? s.created_at.slice(0,10) : '—'}</span></div>
    <div class="acc-row"><span class="acc-lbl">Poslední přihlášení</span><span class="acc-val">${s.last_login ? s.last_login.slice(0,10) : '—'}</span></div>
  </div>

  <!-- Export dat -->
  <div class="acc-card">
    <div class="acc-card-title">📦 Export dat (GDPR)</div>
    <div class="acc-card-desc">
      Stáhni kompletní kopii všech svých herních dat — postavu, inventář, zlaté transakce, arena historii a achievementy.
    </div>
    <button class="btn btn-outline acc-btn" onclick="accountExport()">⬇ Stáhnout moje data (JSON)</button>
  </div>

  <!-- Anonymizace -->
  <div class="acc-card acc-card-danger-light">
    <div class="acc-card-title">🔒 Anonymizace (GDPR)</div>
    <div class="acc-card-desc">
      Odstraní tvůj email a vzhled postavy. Herní záznamy (level, ELO, achievementy) zůstanou pro integritu žebříčků.
      Tato akce je <strong>nevratná</strong>.
    </div>
    <button class="btn btn-outline acc-btn ${s.anonymized ? 'btn-disabled' : ''}"
            onclick="${s.anonymized ? '' : 'accountAnonymize()'}"
            ${s.anonymized ? 'disabled' : ''}>
      ${s.anonymized ? '✓ Anonymizováno' : '🔒 Anonymizovat účet'}
    </button>
  </div>

  <!-- Smazání -->
  <div class="acc-card acc-card-danger">
    <div class="acc-card-title">🗑 Smazání účtu</div>
    <div class="acc-card-desc">
      Označí účet ke smazání. Data budou zachována <strong>30 dní</strong>, poté trvale odstraněna.
      Během 30 dní se můžeš přihlásit a smazání zrušit.
    </div>
    ${s.is_deleted
      ? `<button class="btn btn-outline acc-btn" onclick="accountCancelDelete()">↩ Zrušit smazání</button>`
      : `<button class="btn btn-danger acc-btn" onclick="accountRequestDelete()">🗑 Smazat účet</button>`
    }
  </div>

</div>
  `;
}

async function accountExport() {
  try {
    const data = await api('GET', '/account/export');
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dungeon_chronicles_export_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Data exportována — soubor byl stažen.', 's');
  } catch (e) {
    toast('Export se nezdařil.', 'e');
  }
}

async function accountRequestDelete() {
  if (!confirm('Opravdu chceš označit účet ke smazání?\n\nMáš 30 dní na zrušení. Po uplynutí doby budou data trvale odstraněna.')) return;
  try {
    const r = await api('POST', '/account/delete');
    toast(r.message || 'Účet označen ke smazání.', 'i', 6000);
    await loadAccount();
  } catch (e) {
    toast(e.message || 'Chyba při mazání účtu.', 'e');
  }
}

async function accountCancelDelete() {
  try {
    const r = await api('POST', '/account/delete/cancel');
    toast(r.message || 'Smazání zrušeno.', 's');
    await loadAccount();
  } catch (e) {
    toast(e.message || 'Chyba při rušení smazání.', 'e');
  }
}

async function accountAnonymize() {
  if (!confirm('Anonymizace je nevratná.\n\nTvůj email a vzhled postavy budou odstraněny. Herní data zůstanou.\n\nPokračovat?')) return;
  try {
    const r = await api('POST', '/account/anonymize');
    toast(r.message || 'Účet anonymizován.', 's', 6000);
    await loadAccount();
  } catch (e) {
    toast(e.message || 'Chyba při anonymizaci.', 'e');
  }
}
