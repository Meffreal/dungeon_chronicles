// frontend/js/bugs.js — Bug Report modal & submit

async function submitBugReport() {
  const title       = document.getElementById('br-title').value.trim();
  const description = document.getElementById('br-description').value.trim();
  const steps       = document.getElementById('br-steps').value.trim();
  const severity    = document.getElementById('br-severity').value;
  const pageContext = document.getElementById('br-page-context').value;

  if (!title || title.length < 3) {
    toast('Zadej název bugu (min. 3 znaky).', 'e'); return;
  }
  if (!description || description.length < 10) {
    toast('Popis je příliš krátký (min. 10 znaků).', 'e'); return;
  }

  const btn = document.getElementById('br-submit-btn');
  btn.disabled = true;
  btn.textContent = 'Odesílám...';

  try {
    await api('POST', '/bugs/report', {
      title,
      description,
      steps: steps || null,
      severity,
      page_context: pageContext || null,
    });
    toast('Díky za report! Budeme se tím zabývat.', 's');
    _resetBugReportForm();
    closeModal('modal-bug-report');
  } catch (e) {
    const msg = e?.message || '';
    if (msg.includes('429')) {
      toast('Denní limit reportů byl dosažen (max 5/den).', 'e');
    } else {
      toast('Chyba při odesílání reportu.', 'e');
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Odeslat report';
  }
}

function _resetBugReportForm() {
  ['br-title', 'br-description', 'br-steps'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const sev = document.getElementById('br-severity');
  if (sev) sev.value = 'minor';
}

function openBugReportModal() {
  // Detekce aktivní stránky z DOM
  const activePage = document.querySelector('.page.active');
  const pageCtx = document.getElementById('br-page-context');
  if (pageCtx && activePage) {
    pageCtx.value = activePage.id || '';
  }
  openModal('modal-bug-report');
}
