// ── DICEBEAR ADVENTURER APPEARANCE SYSTEM ────────────────────────────────────
console.log('[APPEARANCE.JS] DiceBear Adventurer modal system loaded');

let appearanceOptions = null;
let currentAppearance = null;

// ── CONSTANTS ─────────────────────────────────────────────────────────────────

/**
 * Official DiceBear Adventurer skin colors (hex) per API documentation
 */
const OFFICIAL_SKIN_COLORS = [
  { name: 'Bledá',    hex: 'fdbdbb' },
  { name: 'Světlá',  hex: 'f4a89f' },
  { name: 'Střední', hex: 'd4a373' },
  { name: 'Bronzová',hex: 'c49a6e' },
  { name: 'Hnědá',   hex: '9e5622' },
  { name: 'Tmavá',   hex: '5d4440' },
];

/**
 * Hair color presets — curated palette compatible with DiceBear hex format
 */
const HAIR_COLOR_PRESETS = [
  { name: 'Černá',       hex: '0e0e0e' },
  { name: 'Tmavě hnědá', hex: '3b1f14' },
  { name: 'Hnědá',       hex: '77311d' },
  { name: 'Kaštanová',   hex: '9b3b1c' },
  { name: 'Zrzavá',      hex: 'c04b16' },
  { name: 'Zlatavá',     hex: 'd4a017' },
  { name: 'Blond',       hex: 'f4d35e' },
  { name: 'Bílá',        hex: 'efefef' },
  { name: 'Stříbrná',    hex: 'a8a8a8' },
  { name: 'Modrá',       hex: '4a7cf7' },
  { name: 'Fialová',     hex: '8b4fe0' },
  { name: 'Zelená',      hex: '2ea84a' },
];

/**
 * Variant arrays for slider-based controls
 * Per DiceBear Adventurer v9.x documentation
 */
const VARIANT_ARRAYS = {
  eyes:     Array.from({ length: 26 }, (_, i) => `variant${String(i + 1).padStart(2, '0')}`),
  eyebrows: Array.from({ length: 15 }, (_, i) => `variant${String(i + 1).padStart(2, '0')}`),
  mouth:    Array.from({ length: 30 }, (_, i) => `variant${String(i + 1).padStart(2, '0')}`),
};

const HAIR_OPTIONS = [
  'long01','long02','long03','long04','long05','long06','long07','long08','long09','long10',
  'long11','long12','long13','long14','long15','long16','long17','long18','long19','long20',
  'long21','long22','long23','long24','long25','long26',
  'short01','short02','short03','short04','short05','short06','short07','short08','short09','short10',
  'short11','short12','short13','short14','short15','short16','short17','short18','short19',
];

const EARRING_VARIANTS = ['variant01','variant02','variant03','variant04','variant05','variant06'];
const GLASSES_VARIANTS = ['variant01','variant02','variant03','variant04','variant05'];
const FEATURES_OPTIONS = [
  { v: 'birthmark', label: 'Znaménko' },
  { v: 'blush',     label: 'Červenání' },
  { v: 'freckles',  label: 'Pihy' },
  { v: 'mustache',  label: 'Knír' },
];

/**
 * Background color presets for DiceBear avatar
 */
const BG_COLOR_PRESETS = [
  { name: 'Černá',          hex: '000000' },
  { name: 'Půlnoční',       hex: '0e0e1e' },
  { name: 'Tmavě modrá',    hex: '0a1428' },
  { name: 'Tmavě fialová',  hex: '14082a' },
  { name: 'Tmavě zelená',   hex: '081a10' },
  { name: 'Tmavě červená',  hex: '1a0808' },
  { name: 'Vínová',         hex: '1a0818' },
  { name: 'Kamenná',        hex: '181820' },
];

// ── API LOADERS ───────────────────────────────────────────────────────────────

async function loadAppearanceOptions() {
  try {
    if (typeof api !== 'function') {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const response = await api('GET', '/character/appearance/options');
    appearanceOptions = response;
    return response;
  } catch (err) {
    console.error('[Appearance] Failed to load options:', err);
    return null;
  }
}

async function loadCurrentAppearance() {
  try {
    if (typeof api !== 'function') {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const data = await api('GET', '/character/appearance');
    currentAppearance = data.appearance;
    return data;
  } catch (err) {
    console.error('[Appearance] Failed to load appearance:', err);
    return null;
  }
}

// ── AVATAR URL BUILDER ────────────────────────────────────────────────────────

/**
 * DiceBear has low DEFAULT probabilities for optional features:
 *   earringsProbability = 10  (default)
 *   glassesProbability  = 10  (default)
 *   featuresProbability = 5   (default)
 * Without explicitly setting these to 100, selected variants may not appear.
 * When the array is empty, we set probability=0 to reliably hide the feature.
 */
const _PROB_FIELDS = {
  earrings: 'earringsProbability',
  glasses:  'glassesProbability',
  features: 'featuresProbability',
};

/**
 * Build DiceBear avatar URL from appearance dict.
 * Background is always black. Identical logic to getAvatarUrl() in api.js.
 */
function buildAvatarUrl(appearance, characterId) {
  const base = 'https://api.dicebear.com/9.x/adventurer/svg';
  const params = new URLSearchParams();

  const seed = appearance?.seed || String(characterId);
  params.append('seed', seed);

  for (const [key, value] of Object.entries(appearance || {})) {
    if (key === 'seed' || value === null || value === undefined) continue;
    if (key === 'background') continue;   // přeskočit background pattern, ne backgroundColor

    if (Array.isArray(value)) {
      if (value.length === 0) {
        // Empty array — explicitly set probability=0 so DiceBear never shows this feature
        if (_PROB_FIELDS[key]) params.append(_PROB_FIELDS[key], '0');
        continue;
      }
      params.append(key, value.join(','));
      // Non-empty — set probability=100 so the selected variant always appears
      if (_PROB_FIELDS[key]) params.append(_PROB_FIELDS[key], '100');
    } else if (typeof value === 'boolean') {
      params.append(key, value.toString());
    } else {
      params.append(key, String(value));
    }
  }

  // Fallback na černé pozadí pokud není v appearance
  if (!appearance?.backgroundColor) {
    params.append('backgroundColor', '000000');
  }
  return `${base}?${params.toString()}`;
}

// ── MODAL OPEN / CLOSE ────────────────────────────────────────────────────────

/**
 * Open the appearance customization modal.
 * Initializes state from current char and renders all controls.
 */
async function openAppearanceModal() {
  if (typeof char === 'undefined' || !char) {
    if (typeof toast === 'function') toast('Nejdříve vytvoř postavu.', 'e');
    return;
  }

  // Always start from the last persisted state to discard any previous unsaved edits
  if (char.appearance) {
    currentAppearance = { ...char.appearance };
  } else if (!currentAppearance) {
    await loadCurrentAppearance();
    if (!currentAppearance) {
      if (typeof toast === 'function') toast('Nepodařilo se načíst vzhled.', 'e');
      return;
    }
  }

  // Lazy-load option definitions (only needed for validation, cached after first load)
  if (!appearanceOptions) {
    await loadAppearanceOptions();
  }

  _renderAppearanceModalBody();

  const overlay = document.getElementById('modal-appearance');
  if (overlay) overlay.classList.add('open');
}

/**
 * Close the appearance modal without saving.
 */
function closeAppearanceModal() {
  const overlay = document.getElementById('modal-appearance');
  if (overlay) overlay.classList.remove('open');
}

// ── MODAL RENDERING ───────────────────────────────────────────────────────────

/**
 * Render all appearance controls into #appearance-modal-body.
 * Called on open and after reset.
 */
function _renderAppearanceModalBody() {
  const body = document.getElementById('appearance-modal-body');
  if (!body) return;

  if (!currentAppearance) {
    body.innerHTML = '<div style="text-align:center;color:var(--accent);padding:30px">❌ Vzhled není dostupný</div>';
    return;
  }

  const app = currentAppearance;
  const characterId = (typeof char !== 'undefined' && char?.id) ? char.id : 'avatar';
  const charName = (typeof char !== 'undefined' && char?.name) ? esc(char.name) : '';

  // Resolve current selections with safe defaults
  const skinSelected     = Array.isArray(app.skinColor)  && app.skinColor.length  ? app.skinColor[0]  : OFFICIAL_SKIN_COLORS[4].hex;
  const hairColorSelected= Array.isArray(app.hairColor)  && app.hairColor.length  ? app.hairColor[0]  : HAIR_COLOR_PRESETS[0].hex;
  const hairSelected     = Array.isArray(app.hair)        && app.hair.length        ? app.hair[0]        : 'long01';
  const hairIdx          = Math.max(0, HAIR_OPTIONS.indexOf(hairSelected));
  const eyesSelected     = Array.isArray(app.eyes)        && app.eyes.length        ? app.eyes[0]        : 'variant01';
  const eyesIdx          = Math.max(0, VARIANT_ARRAYS.eyes.indexOf(eyesSelected));
  const eyebrowsSelected = Array.isArray(app.eyebrows)    && app.eyebrows.length    ? app.eyebrows[0]    : 'variant01';
  const eyebrowsIdx      = Math.max(0, VARIANT_ARRAYS.eyebrows.indexOf(eyebrowsSelected));
  const mouthSelected    = Array.isArray(app.mouth)       && app.mouth.length       ? app.mouth[0]       : 'variant01';
  const mouthIdx         = Math.max(0, VARIANT_ARRAYS.mouth.indexOf(mouthSelected));
  const earringSelected  = Array.isArray(app.earrings)    && app.earrings.length    ? app.earrings[0]    : null;
  const glassesSelected  = Array.isArray(app.glasses)     && app.glasses.length     ? app.glasses[0]     : null;
  const featuresSelected = Array.isArray(app.features)    ? app.features : [];
  const bgColorSelected  = app.backgroundColor || '000000';

  const avatarUrl = buildAvatarUrl(app, characterId);

  body.innerHTML = `
    <div class="apm-layout">

      <!-- ── Left column: preview + action buttons ── -->
      <div class="apm-preview-col">
        <div class="apm-avatar-wrap">
          <img id="appearance-avatar" src="${avatarUrl}" alt="Avatar" class="apm-avatar-img"
               onerror="this.style.display='none';document.getElementById('appearance-fallback').style.display='flex'">
          <div id="appearance-fallback"
               style="display:none;width:100%;height:100%;align-items:center;justify-content:center;font-size:4rem">🧙</div>
        </div>
        ${charName ? `<div class="apm-preview-name">${charName}</div>` : ''}
        <button class="btn btn-green apm-btn" id="app-save-btn" onclick="saveAppearance()">💾 Uložit vzhled</button>
        <button class="btn btn-secondary apm-btn" onclick="resetAppearance()">↺ Resetovat</button>
      </div>

      <!-- ── Right column: all customization options ── -->
      <div class="apm-options-col">

        <!-- Skin color -->
        <div class="apm-section">
          <div class="apm-section-title">⬤ Barva kůže</div>
          <div class="appearance-swatch-container apm-skin-swatches">
            ${OFFICIAL_SKIN_COLORS.map(c => `
              <div class="appearance-swatch ${skinSelected === c.hex ? 'active' : ''}"
                   style="background-color:#${c.hex}" title="${c.name}"
                   data-hex="${c.hex}"
                   onclick="setSkinColor('${c.hex}')"></div>
            `).join('')}
          </div>
        </div>

        <!-- Hair style -->
        <div class="apm-section">
          <div class="apm-section-title">💇 Styl vlasů</div>
          <div class="appearance-slider-group">
            <input type="range" id="app-hair" min="0" max="${HAIR_OPTIONS.length - 1}" value="${hairIdx}"
                   class="appearance-slider" oninput="updateHairSelection('hair')">
            <span class="appearance-slider-value" id="app-hair-val">${hairSelected}</span>
          </div>
        </div>

        <!-- Hair color -->
        <div class="apm-section">
          <div class="apm-section-title">🎨 Barva vlasů</div>
          <div class="appearance-swatch-container apm-hair-swatches">
            ${HAIR_COLOR_PRESETS.map(c => `
              <div class="appearance-swatch apm-swatch-sm ${hairColorSelected === c.hex ? 'active' : ''}"
                   style="background-color:#${c.hex}" title="${c.name}"
                   data-hex="${c.hex}"
                   onclick="setHairColor('${c.hex}')"></div>
            `).join('')}
          </div>
        </div>

        <!-- Eyes -->
        <div class="apm-section">
          <div class="apm-section-title">👀 Oči</div>
          <div class="appearance-slider-group">
            <input type="range" id="app-eyes" min="0" max="${VARIANT_ARRAYS.eyes.length - 1}" value="${eyesIdx}"
                   class="appearance-slider" oninput="updateVariantSlider('eyes')">
            <span class="appearance-slider-value" id="app-eyes-val">${eyesSelected}</span>
          </div>
        </div>

        <!-- Eyebrows -->
        <div class="apm-section">
          <div class="apm-section-title">🤨 Obočí</div>
          <div class="appearance-slider-group">
            <input type="range" id="app-eyebrows" min="0" max="${VARIANT_ARRAYS.eyebrows.length - 1}" value="${eyebrowsIdx}"
                   class="appearance-slider" oninput="updateVariantSlider('eyebrows')">
            <span class="appearance-slider-value" id="app-eyebrows-val">${eyebrowsSelected}</span>
          </div>
        </div>

        <!-- Mouth -->
        <div class="apm-section">
          <div class="apm-section-title">👄 Ústa</div>
          <div class="appearance-slider-group">
            <input type="range" id="app-mouth" min="0" max="${VARIANT_ARRAYS.mouth.length - 1}" value="${mouthIdx}"
                   class="appearance-slider" oninput="updateVariantSlider('mouth')">
            <span class="appearance-slider-value" id="app-mouth-val">${mouthSelected}</span>
          </div>
        </div>

        <!-- Earrings -->
        <div class="apm-section">
          <div class="apm-section-title">💍 Náušnice</div>
          <div class="appearance-option-buttons">
            <button class="appearance-option-btn ${earringSelected === null ? 'active' : ''}"
                    data-one-field="earrings" data-one-value="none"
                    onclick="selectOneVariant('earrings', null)">✕ Žádné</button>
            ${EARRING_VARIANTS.map(v => `
              <button class="appearance-option-btn ${earringSelected === v ? 'active' : ''}"
                      data-one-field="earrings" data-one-value="${v}"
                      onclick="selectOneVariant('earrings', '${v}')">
                ${_fmtVariant(v)}
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Glasses -->
        <div class="apm-section">
          <div class="apm-section-title">👓 Brýle</div>
          <div class="appearance-option-buttons">
            <button class="appearance-option-btn ${glassesSelected === null ? 'active' : ''}"
                    data-one-field="glasses" data-one-value="none"
                    onclick="selectOneVariant('glasses', null)">✕ Žádné</button>
            ${GLASSES_VARIANTS.map(v => `
              <button class="appearance-option-btn ${glassesSelected === v ? 'active' : ''}"
                      data-one-field="glasses" data-one-value="${v}"
                      onclick="selectOneVariant('glasses', '${v}')">
                ${_fmtVariant(v)}
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Facial features -->
        <div class="apm-section">
          <div class="apm-section-title">✨ Znaky tváře</div>
          <div class="appearance-option-buttons">
            ${FEATURES_OPTIONS.map(f => `
              <button class="appearance-option-btn ${featuresSelected.includes(f.v) ? 'active' : ''}"
                      data-field="features"
                      data-value="${f.v}"
                      onclick="toggleArrayValue('features', '${f.v}')">
                ${f.label}
              </button>
            `).join('')}
          </div>
        </div>

        <!-- Background color -->
        <div class="apm-section">
          <div class="apm-section-title">🌌 Barva pozadí</div>
          <div class="appearance-swatch-container apm-bg-swatches">
            ${BG_COLOR_PRESETS.map(c => `
              <div class="apm-bg-swatch ${bgColorSelected === c.hex ? 'active' : ''}"
                   style="background-color:#${c.hex};outline:1px solid rgba(255,255,255,.08)" title="${c.name}"
                   data-hex="${c.hex}"
                   onclick="setBgColor('${c.hex}')"></div>
            `).join('')}
          </div>
        </div>

      </div><!-- /apm-options-col -->
    </div><!-- /apm-layout -->
  `;
}

/** Short display label for variant strings: "variant01" → "v1", "variant12" → "v12" */
function _fmtVariant(v) {
  return v.replace(/variant0*(\d+)/, 'v$1');
}

// ── INTERACTION HANDLERS ──────────────────────────────────────────────────────

/**
 * Set skin color from swatch — scoped to skin swatches only
 */
function setSkinColor(hexValue) {
  if (!OFFICIAL_SKIN_COLORS.find(c => c.hex === hexValue)) {
    console.error('[Appearance] Invalid skin color:', hexValue);
    return;
  }
  currentAppearance['skinColor'] = [hexValue];
  document.querySelectorAll('.apm-skin-swatches .appearance-swatch').forEach(el => {
    el.classList.toggle('active', el.dataset.hex === hexValue);
  });
  refreshAvatarPreview();
}

/**
 * Set hair color from swatch — scoped to hair swatches only
 */
function setHairColor(hexValue) {
  if (!HAIR_COLOR_PRESETS.find(c => c.hex === hexValue)) {
    console.error('[Appearance] Invalid hair color:', hexValue);
    return;
  }
  currentAppearance['hairColor'] = [hexValue];
  document.querySelectorAll('.apm-hair-swatches .appearance-swatch').forEach(el => {
    el.classList.toggle('active', el.dataset.hex === hexValue);
  });
  refreshAvatarPreview();
}

/**
 * Set background color from swatch
 */
function setBgColor(hexValue) {
  if (!BG_COLOR_PRESETS.find(c => c.hex === hexValue)) {
    console.error('[Appearance] Invalid bg color:', hexValue);
    return;
  }
  currentAppearance['backgroundColor'] = hexValue;
  document.querySelectorAll('.apm-bg-swatches .apm-bg-swatch').forEach(el => {
    el.classList.toggle('active', el.dataset.hex === hexValue);
  });
  refreshAvatarPreview();
}

/**
 * Update hair style from slider (maps 0-44 index → HAIR_OPTIONS name)
 */
function updateHairSelection(fieldName) {
  const elem = document.getElementById(`app-${fieldName}`);
  if (!elem) return;
  const index = parseInt(elem.value);
  const selected = HAIR_OPTIONS[index] || 'long01';
  currentAppearance['hair'] = [selected];
  const valDisplay = document.getElementById(`app-${fieldName}-val`);
  if (valDisplay) valDisplay.textContent = selected;
  refreshAvatarPreview();
}

/**
 * Update a variant slider field (eyes, eyebrows, mouth)
 * Maps 0-based slider index → "variantXX" name
 */
function updateVariantSlider(fieldName) {
  const elem = document.getElementById(`app-${fieldName}`);
  if (!elem) return;
  const variants = VARIANT_ARRAYS[fieldName];
  if (!variants) return;
  const index = parseInt(elem.value);
  const selected = variants[index] || variants[0];
  currentAppearance[fieldName] = [selected];
  const valDisplay = document.getElementById(`app-${fieldName}-val`);
  if (valDisplay) valDisplay.textContent = selected;
  refreshAvatarPreview();
}

/**
 * Single-select a variant option (earrings, glasses).
 * value=null means "none" (empty array).
 */
function selectOneVariant(fieldName, value) {
  currentAppearance[fieldName] = value === null ? [] : [value];
  document.querySelectorAll(`[data-one-field="${fieldName}"]`).forEach(btn => {
    const isNone  = btn.dataset.oneValue === 'none';
    const isMatch = btn.dataset.oneValue === value;
    btn.classList.toggle('active', value === null ? isNone : isMatch);
  });
  refreshAvatarPreview();
}

/**
 * Toggle a value in an array field (features — multi-select).
 */
function toggleArrayValue(fieldName, value) {
  if (!currentAppearance[fieldName]) {
    currentAppearance[fieldName] = [];
  }
  const arr = currentAppearance[fieldName];
  const idx = arr.indexOf(value);
  if (idx > -1) {
    arr.splice(idx, 1);
  } else {
    arr.push(value);
  }
  document.querySelectorAll(`[data-field="${fieldName}"][data-value]`).forEach(btn => {
    btn.classList.toggle('active', arr.includes(btn.dataset.value));
  });
  refreshAvatarPreview();
}

/**
 * Update a boolean or integer scalar field
 */
function updateField(fieldName) {
  const elem = document.getElementById(`app-${fieldName}`);
  if (!elem) return;
  let value;
  if (elem.type === 'checkbox') {
    value = elem.checked;
  } else if (elem.type === 'range' || elem.type === 'number') {
    value = parseInt(elem.value);
    const valDisplay = document.getElementById(`app-${fieldName}-val`);
    if (valDisplay) valDisplay.textContent = value;
  } else {
    value = elem.value;
  }
  currentAppearance[fieldName] = value;
  refreshAvatarPreview();
}

/**
 * Refresh the avatar preview image inside the modal in real time
 */
function refreshAvatarPreview() {
  const img = document.getElementById('appearance-avatar');
  if (!img) return;
  const characterId = (typeof char !== 'undefined' && char?.id) ? char.id : 'avatar';
  img.src = buildAvatarUrl(currentAppearance, characterId);
  img.style.display = 'block';
  const fallback = document.getElementById('appearance-fallback');
  if (fallback) fallback.style.display = 'none';
}

// ── SAVE / RESET ──────────────────────────────────────────────────────────────

/**
 * Validate, persist appearance to backend, sync global state, close modal.
 */
async function saveAppearance() {
  const btn = document.getElementById('app-save-btn');
  if (!btn) return;

  // Validate skin color — must be from official palette
  const skinColor = currentAppearance['skinColor'];
  if (skinColor && Array.isArray(skinColor) && skinColor.length > 0) {
    if (!OFFICIAL_SKIN_COLORS.some(c => c.hex === skinColor[0])) {
      if (typeof toast === 'function') toast('❌ Neplatná barva kůže.', 'e');
      return;
    }
  }

  // Validate hair color — must be a valid 6-digit hex
  const hairColor = currentAppearance['hairColor'];
  if (hairColor && Array.isArray(hairColor) && hairColor.length > 0) {
    if (!/^[a-fA-F0-9]{6}$/.test(String(hairColor[0]))) {
      if (typeof toast === 'function') toast('❌ Neplatná barva vlasů.', 'e');
      return;
    }
  }

  // Validate earring variant if set
  const earrings = currentAppearance['earrings'];
  if (earrings && earrings.length > 0 && !EARRING_VARIANTS.includes(earrings[0])) {
    if (typeof toast === 'function') toast('❌ Neplatná varianta náušnic.', 'e');
    return;
  }

  // Validate glasses variant if set
  const glasses = currentAppearance['glasses'];
  if (glasses && glasses.length > 0 && !GLASSES_VARIANTS.includes(glasses[0])) {
    if (typeof toast === 'function') toast('❌ Neplatná varianta brýlí.', 'e');
    return;
  }

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Ukládám...';

  try {
    console.log('[Appearance] Saving:', currentAppearance);
    const result = await api('POST', '/character/appearance', currentAppearance);

    if (result.character) {
      await syncCharacterState(result.character);
      // Keep local currentAppearance in sync with what the server confirmed
      if (result.character.appearance) {
        currentAppearance = { ...result.character.appearance };
      }
    }

    // Close modal after successful save
    closeAppearanceModal();

    if (typeof toast === 'function') {
      toast('✨ Vzhled uložen a aktualizován!', 's');
    }
  } catch (err) {
    console.error('[Appearance] Save error:', err);
    if (typeof toast === 'function') {
      toast(`Chyba při ukládání: ${err.message}`, 'e');
    }
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

/**
 * Reset to DiceBear Adventurer defaults, re-render modal, then save.
 */
async function resetAppearance() {
  if (!confirm('Opravdu chceš resetovat vzhled na výchozí hodnoty?')) return;

  currentAppearance = {
    seed: 'default',
    base: ['default'],
    scale: 100,
    radius: 0,
    translateX: 0,
    translateY: 0,
    clip: true,
    randomizeIds: false,
    flip: false,
    rotate: 0,
    eyebrows: ['variant01'],
    eyes: ['variant01'],
    features: [],
    mouth: ['variant01'],
    hair: ['long01'],
    hairColor: ['0e0e0e'],
    skinColor: ['9e5622'],
    earrings: [],
    glasses: [],
    backgroundColor: '000000',
  };

  // Re-render modal body with reset values (modal stays open)
  _renderAppearanceModalBody();

  // Persist to backend
  await saveAppearance();
}
