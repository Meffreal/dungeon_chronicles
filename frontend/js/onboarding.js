// ── ONBOARDING TOUR ────────────────────────────────────────────────────────────
// 6-krokový průvodce pro nové hráče.
// Spustí se automaticky po vytvoření postavy nebo při prvním loginu bez dokončeného onboardingu.
//
// Veřejné API:
//   startOnboarding()   — spustí průvodce od kroku 1
//   closeOnboarding()   — zavře průvodce a zavolá API pro uložení stavu

const ONBOARDING_STEPS = [
  {
    icon:   '🏰',
    title:  'Vítej v Dungeon Chronicles!',
    desc:   'Jsi hrdina v temném světě plném nebezpečí a pokladů. Projdeme spolu 6 základních kroků, aby ses rychle zorientoval.',
    target: null,
    btnLabel: 'Začít průvodce →',
  },
  {
    icon:   '⚔️',
    title:  'Quest Log — tvůj zdroj akcí',
    desc:   'Questy jsou tvůj hlavní zdroj XP, zlata a vybavení. Vyber si Lehký quest, spusť ho a počkej na dokončení.',
    target: 'nav-quests',
    btnLabel: 'Jít na Questy →',
    navPage: 'quests',
  },
  {
    icon:   '🛡️',
    title:  'Equipment — nasaď vybavení',
    desc:   'Po každém splněném questu získáš předměty. Přejdi do Equipment a equip vše co jsi dostal pro lepší bojové statistiky.',
    target: 'nav-equipment',
    btnLabel: 'Jít do Equipment →',
    navPage: 'equipment',
  },
  {
    icon:   '🏆',
    title:  'Aréna — PvP souboje',
    desc:   'Aréna je asynchronní PvP — útočíš na jiné hráče a oni se brání automaticky. Výhry přinášejí ELO rating a gold.',
    target: 'nav-arena',
    btnLabel: 'Jít do Arény →',
    navPage: 'arena',
  },
  {
    icon:   '⚜️',
    title:  'Cech — sociální síla',
    desc:   'Připoj se k cechu pro guild chat, sdílené cíle (guild weekly quests) a týmové bonusy. Silnější hráči pomáhají slabším.',
    target: 'nav-guild',
    btnLabel: 'Jít na Cechy →',
    navPage: 'guild',
  },
  {
    icon:   '🗺️',
    title:  'Prozkoumej vše ostatní!',
    desc:   'Navigace vlevo skrývá Dungeony, World Boss, Prestiž, Sezónní výzvy, Crystal shop a mnoho dalšího. Hodně štěstí, hrdino!',
    target: null,
    btnLabel: '🎉 Začít hrát!',
  },
];

let _obStep       = 0;
let _obActive     = false;
let _obHighlighted = null;  // currently highlighted DOM element

// ── Veřejné API ────────────────────────────────────────────────────────────────

function startOnboarding() {
  if (_obActive) return;
  _obActive = true;
  _obStep   = 0;
  _renderObStep();
}

function closeOnboarding(markComplete = true) {
  _obActive = false;
  _clearHighlight();
  document.getElementById('ob-backdrop')?.remove();
  document.getElementById('ob-card')?.remove();
  if (markComplete) {
    api('POST', '/character/complete-onboarding').catch(() => {});
  }
}

// ── Rendering ──────────────────────────────────────────────────────────────────

function _renderObStep() {
  const step  = ONBOARDING_STEPS[_obStep];
  const total = ONBOARDING_STEPS.length;

  // Backdrop
  let backdrop = document.getElementById('ob-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id        = 'ob-backdrop';
    backdrop.className = 'ob-backdrop';
    backdrop.addEventListener('click', _onBackdropClick);
    document.body.appendChild(backdrop);
  }

  // Dots HTML
  const dots = ONBOARDING_STEPS.map((_, i) =>
    `<div class="ob-dot ${i === _obStep ? 'active' : ''}"></div>`
  ).join('');

  // Card
  let card = document.getElementById('ob-card');
  if (!card) {
    card = document.createElement('div');
    card.id        = 'ob-card';
    card.className = 'ob-card';
    document.body.appendChild(card);
  }

  const isLast = _obStep === total - 1;

  card.innerHTML = `
    <div class="ob-step-num">Krok ${_obStep + 1} z ${total}</div>
    <div class="ob-icon">${step.icon}</div>
    <div class="ob-title">${esc(step.title)}</div>
    <div class="ob-desc">${esc(step.desc)}</div>
    <div class="ob-dots">${dots}</div>
    <div class="ob-actions">
      <button class="ob-btn-skip" onclick="closeOnboarding(true)">Přeskočit vše</button>
      <button class="ob-btn-next" onclick="_obNext()">${esc(step.btnLabel)}</button>
    </div>`;

  // Highlight nav target
  _clearHighlight();
  if (step.target) {
    const el = document.getElementById(step.target);
    if (el) {
      el.classList.add('ob-highlight-target');
      _obHighlighted = el;
    }
  }
}

function _obNext() {
  const step  = ONBOARDING_STEPS[_obStep];
  const total = ONBOARDING_STEPS.length;

  // Navigate to page if step has navPage
  if (step.navPage && typeof showPage === 'function') {
    showPage(step.navPage);
  }

  _obStep++;

  if (_obStep >= total) {
    closeOnboarding(true);
    return;
  }

  // Re-render card with new step (slight animation reset)
  const card = document.getElementById('ob-card');
  if (card) {
    card.style.animation = 'none';
    void card.offsetWidth;
    card.style.animation = '';
  }
  _renderObStep();
}

function _onBackdropClick(e) {
  // Kliknutí mimo kartu = přeskočit (ale neoznačí za dokončené — jen zavře)
  if (e.target === document.getElementById('ob-backdrop')) {
    closeOnboarding(false);
  }
}

function _clearHighlight() {
  if (_obHighlighted) {
    _obHighlighted.classList.remove('ob-highlight-target');
    _obHighlighted = null;
  }
  // Bezpečnostní čistění
  document.querySelectorAll('.ob-highlight-target').forEach(el =>
    el.classList.remove('ob-highlight-target')
  );
}
