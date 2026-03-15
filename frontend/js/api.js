// ── API CORE ──────────────────────────────────────────────────────────────
const API = window.location.origin;
let token = localStorage.getItem('dc_token');

// In-flight GET request deduplication: same URL returns same promise
const _inflight = new Map();

async function api(method, path, body) {
  // Deduplicate parallel GET requests to the same URL
  // (prevents double-fetches when multiple components init at once)
  const dedupeKey = method === 'GET' ? path : null;
  if (dedupeKey && _inflight.has(dedupeKey)) {
    return _inflight.get(dedupeKey);
  }

  const promise = _doFetch(method, path, body).finally(() => {
    if (dedupeKey) _inflight.delete(dedupeKey);
  });

  if (dedupeKey) _inflight.set(dedupeKey, promise);
  return promise;
}

async function _doFetch(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: { 'Content-Type':'application/json', ...(token?{Authorization:`Bearer ${token}`}:{}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  let d;
  try { d = await r.json(); } catch { throw new Error('Chyba serveru (500)'); }
  if (!r.ok) {
    const err = new Error(typeof d.detail === 'string' ? d.detail : (d.detail?.msg || 'Chyba serveru'));
    err.detail = d.detail;
    err.status  = r.status;
    throw err;
  }
  return d;
}

// ── THEME COLOR UTILITIES ──────────────────────────────────────────────────
/**
 * Get the current theme's primary accent color for avatar backgrounds.
 * Reads from CSS variables: tries --accent first, falls back to --accent2, then --bg2
 * Returns hex color WITHOUT the # prefix (required by DiceBear API)
 */
function getAvatarBackgroundColor() {
  try {
    // Get computed styles from document root
    const style = getComputedStyle(document.documentElement);
    
    // Try primary accent color first
    let color = style.getPropertyValue('--accent').trim();
    if (!color) {
      // Fallback to secondary accent
      color = style.getPropertyValue('--accent2').trim();
    }
    if (!color) {
      // Fallback to background2
      color = style.getPropertyValue('--bg2').trim();
    }
    if (!color) {
      // Final fallback to safe default (dark blue matching theme)
      color = '#1e7fb8';
    }
    
    // Normalize: remove # if present
    color = color.replace('#', '').trim();
    
    // Ensure valid hex format (6 chars)
    if (!/^[0-9a-f]{6}$/i.test(color)) {
      console.warn('[Theme] Invalid color format:', color, 'using fallback');
      color = '1e7fb8'; // Safe default
    }
    
    console.log('[Theme] Avatar background color:', color);
    return color;
  } catch (err) {
    console.error('[Theme] Error reading theme color:', err);
    return '1e7fb8'; // Safe fallback
  }
}
// ── DICEBEAR AVATAR GENERATOR ──────────────────────────────────────────────
/**
 * Generate a DiceBear avatar URL based on appearance and character ID.
 * Supports BOTH old format (hair_style, eye_color numeric) and new format (seed, hair/eyes arrays)
 * Uses DiceBear API directly: https://api.dicebear.com/9.x/adventurer/svg
 * Avatar backgroundColor is always overridden with the current theme accent color.
 * 
 * IMPORTANT: Must produce IDENTICAL URLs as buildAvatarUrl() in appearance.js
 * (except backgroundColor which is theme-driven)
 */
function getAvatarUrl(appearance, characterId = 'default') {
  console.log('[DiceBear] getAvatarUrl called:', { appearance, characterId });
  
  // DETECT FORMAT: Check if this is the new DiceBear format or old format
  const isNewFormat = appearance && (
    Array.isArray(appearance.hair) ||
    Array.isArray(appearance.eyes) ||
    appearance.seed ||
    appearance.backgroundColor
  );
  
  console.log('[DiceBear] Format detected:', isNewFormat ? 'NEW' : 'OLD');
  
  const base = 'https://api.dicebear.com/9.x/adventurer/svg';
  const params = new URLSearchParams();
  
  // Get current theme background color
  const themeBackgroundColor = getAvatarBackgroundColor();
  console.log('[DiceBear] Using theme background color:', themeBackgroundColor);
  
  if (isNewFormat) {
    // NEW FORMAT: Match buildAvatarUrl() exactly, but override backgroundColor
    console.log('[DiceBear] Using NEW format parser - matching buildAvatarUrl()');
    
    // Use character ID as seed if not explicitly set
    const seed = appearance?.seed || String(characterId);
    params.append('seed', seed);
    
    // Add all fields from appearance dict (same logic as buildAvatarUrl)
    // BUT: Override backgroundColor with theme color
    // Probability fields: DiceBear defaults are low (earrings=10, glasses=10, features=5)
    // so we must set them to 100 when variants are selected, or 0 when empty.
    const _probFields = { earrings: 'earringsProbability', glasses: 'glassesProbability', features: 'featuresProbability' };

    for (const [key, value] of Object.entries(appearance || {})) {
      if (key === 'seed' || value === null || value === undefined) continue;

      // OVERRIDE: Always use theme color for background
      if (key === 'backgroundColor') {
        params.append(key, themeBackgroundColor);
        console.log('[DiceBear] Overriding backgroundColor with theme color:', themeBackgroundColor);
        continue;
      }

      if (Array.isArray(value)) {
        if (value.length === 0) {
          if (_probFields[key]) params.append(_probFields[key], '0');
          continue;
        }
        params.append(key, value.join(','));
        if (_probFields[key]) params.append(_probFields[key], '100');
      } else if (typeof value === 'boolean') {
        params.append(key, value.toString());
      } else {
        params.append(key, value);
      }
    }
  } else {
    // OLD FORMAT: Use numeric mappings
    console.log('[DiceBear] Using OLD format parser');
    
    const hairMap = [
      'short01',  // 0: Kratke rovne
      'long01',   // 1: Dlouhe vlnite
      'long02',   // 2: Kader
      'long03',   // 3: Culik
      'short02',  // 4: Shaved
      'short03',  // 5: Mohawk
      'long04'    // 6: Copanky
    ];
    
    const eyeMap = [
      'variant01', // 0: Hneda
      'variant02', // 1: Modra
      'variant03', // 2: Zelena
      'variant04', // 3: Seda
      'variant05', // 4: Fialova
      'variant06', // 5: Zlata
      'variant07'  // 6: Ruda (Vampyr)
    ];
    
    const seed = characterId || 'default';
    const hair = hairMap[appearance?.hair_style || 0] || 'short01';
    const eyes = eyeMap[appearance?.eye_color || 0] || 'variant01';
    
    params.append('seed', seed);
    params.append('hair', hair);
    params.append('eyes', eyes);
    params.append('scale', 100);
    params.append('backgroundColor', themeBackgroundColor);
    params.append('backgroundType', 'solid');
  }
  
  // Build DiceBear API URL directly
  const url = `${base}?${params.toString()}`;
  console.log('[DiceBear] Generated avatar URL:', url);
  return url;
}

// ── DICEBEAR AVATAR WITH FALLBACK ─────────────────────────────────────────

/**
 * Load avatar with fallback to simple SVG if DiceBear fails
 */
async function loadAvatarWithFallback(appearance, characterId = 'default') {
  const url = getAvatarUrl(appearance, characterId);
  console.log('[Avatar] Attempting to load from DiceBear:', url);
  
  try {
    const response = await fetch(url);
    if (response.ok) {
      const blob = await response.blob();
      const dataUrl = URL.createObjectURL(blob);
      console.log('[Avatar] Successfully loaded from DiceBear');
      return dataUrl;
    }
  } catch (err) {
    console.warn('[Avatar] DiceBear fetch failed:', err);
  }
  
  // Fallback: generate simple SVG avatar locally
  console.log('[Avatar] Using local SVG fallback');
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'];
  const hash = (String(characterId) + JSON.stringify(appearance || {})).split('').reduce((a, b) => a + b.charCodeAt(0), 0);
  const color = colors[hash % colors.length];
  const emoji = ['🧙', '⚔️', '🏹', '👤', '🎭', '💀', '🧛', '🌕'][hash % 8];
  
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">
    <rect fill="${color}" width="120" height="120"/>
    <text x="60" y="60" text-anchor="middle" dy=".3em" fill="white" font-size="60" font-weight="bold">${emoji}</text>
  </svg>`;
  
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

// Alias for backward compatibility
const loadAvatarAsDataUrl = loadAvatarWithFallback;
