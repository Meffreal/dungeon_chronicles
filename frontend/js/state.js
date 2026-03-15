// ── CENTRALIZED STATE MANAGEMENT ──────────────────────────────────────────
// Handles global character state and ensures all UI components stay in sync
// when appearance (avatar) is updated.

console.log('[STATE] Global state management module loaded');

/**
 * Sync character state from API response and update all UI components
 * Call this after any appearance/character update to propagate changes across the app
 */
async function syncCharacterState(updatedCharObj) {
  console.log('[STATE] Syncing character state:', updatedCharObj);
  
  if (!updatedCharObj || !updatedCharObj.id) {
    console.error('[STATE] Invalid character object for sync:', updatedCharObj);
    return false;
  }
  
  // 1. Update global char variable (this is read by all UI components)
  char = updatedCharObj;
  console.log('[STATE] ✓ Updated global char variable');
  
  // 2. Update appearance in global state
  if (updatedCharObj.appearance) {
    currentAppearance = updatedCharObj.appearance;
    console.log('[STATE] ✓ Updated global currentAppearance');
  }
  
  // 3. Refresh all avatar displays in the entire app
  refreshAllAvatars();
  console.log('[STATE] ✓ Refreshed all avatar displays');
  
  // 4. Update UI components that depend on character data
  updateUI(updatedCharObj);
  console.log('[STATE] ✓ Updated main UI components');
  
  // 5. Broadcast custom event for other components to react
  const event = new CustomEvent('characterUpdated', {
    detail: { character: updatedCharObj }
  });
  document.dispatchEvent(event);
  console.log('[STATE] ✓ Dispatched characterUpdated event');
  
  return true;
}

/**
 * Refresh all avatar images across the entire application
 * This handles:
 * - Profile/navbar avatar
 * - Appearance preview
 * - Guild member avatars
 * - Leaderboard avatars
 * - Any other avatar renderings
 */
function refreshAllAvatars() {
  if (!char || !char.appearance || !char.id) {
    console.warn('[STATE] Cannot refresh avatars: missing char data');
    return;
  }
  
  console.log('[STATE] Refreshing all avatars for character:', char.name);
  console.log('[STATE] char.appearance object:', char.appearance);
  console.log('[STATE] char.appearance keys:', Object.keys(char.appearance));
  
  // Build avatar URL once
  let avatarUrl;
  if (buildAvatarUrl) {
    console.log('[STATE] Using buildAvatarUrl from appearance.js');
    avatarUrl = buildAvatarUrl(char.appearance, char.id);
  } else if (getAvatarUrl) {
    console.log('[STATE] Fallback: using getAvatarUrl from api.js');
    avatarUrl = getAvatarUrl(char.appearance, char.id);
  } else {
    console.error('[STATE] No avatar URL builder function available!');
    return;
  }
  
  console.log('[STATE] Generated Avatar URL:', avatarUrl);
  
  // 1. Navbar/profile avatar (main header)
  const profileAvatarImg = document.getElementById('p-avatar-img');
  if (profileAvatarImg) {
    console.log('[STATE] Updating #p-avatar-img to:', avatarUrl);
    profileAvatarImg.src = avatarUrl;
    profileAvatarImg.style.display = 'block';
  }
  
  // 2. Appearance preview (if on appearance page)
  const appearanceAvatar = document.getElementById('appearance-avatar');
  if (appearanceAvatar) {
    console.log('[STATE] Updating #appearance-avatar to:', avatarUrl);
    appearanceAvatar.src = avatarUrl;
    appearanceAvatar.style.display = 'block';
    // Hide fallback
    const fallback = document.getElementById('appearance-fallback');
    if (fallback) fallback.style.display = 'none';
  }
  
  // 3. Equipment portrait avatar (updated directly for immediate feedback)
  const equipAvatarImg = document.getElementById('equip-avatar-img');
  if (equipAvatarImg) {
    equipAvatarImg.src = avatarUrl;
    equipAvatarImg.style.display = 'block';
  }

  // 5. Any other avatar images with data-avatar-for="current"
  document.querySelectorAll('img[data-avatar-for="current"]').forEach(img => {
    console.log('[STATE] Updating avatar image:', img.id || 'unknown', 'to:', avatarUrl);
    img.src = avatarUrl;
    img.style.display = 'block';
  });

  // (Leaderboard and guild member avatars belong to other players — not updated here)
  
  console.log('[STATE] ✓ All avatar displays refreshed');
}

/**
 * Handle character update from any source
 * This is the main entry point for state changes
 */
async function onCharacterUpdated(updatedCharData) {
  console.log('[STATE] Character updated:', updatedCharData);
  
  // If it's from an API response, sync it
  if (updatedCharData && typeof updatedCharData === 'object') {
    await syncCharacterState(updatedCharData);
  } else {
    console.error('[STATE] Invalid character data:', updatedCharData);
  }
}

/**
 * Listen for custom character update events
 */
document.addEventListener('characterUpdated', (e) => {
  console.log('[STATE] Received characterUpdated event:', e.detail);
  // Event already processed by syncCharacterState, this is just for other listeners
});

// Listen for theme changes and refresh avatars
// This observer detects when CSS variables (theme colors) are changed
let themeObserver = null;
function initializeThemeListener() {
  // Watch for changes to the root element's style
  themeObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
        console.log('[STATE] Theme change detected, refreshing avatars...');
        if (char && char.id) {
          refreshAllAvatars();
        }
      }
    }
  });
  
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['style']
  });
  
  console.log('[STATE] Theme change listener initialized');
}

// Also listen for changes to CSS variables via :root class changes
document.addEventListener('themeChanged', () => {
  console.log('[STATE] Theme changed event received, refreshing avatars');
  if (char && char.id) {
    refreshAllAvatars();
  }
});

// Initialize theme listener when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeThemeListener);
} else {
  initializeThemeListener();
}

console.log('[STATE] ✓ State management system initialized');
