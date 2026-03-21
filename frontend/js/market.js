// ── TRŽIŠTĚ ───────────────────────────────────────────────────────────────
let _mktCurrentPage = 1;

async function loadMarket() {
  const search = document.getElementById('mkt-search')?.value || '';
  const type   = document.getElementById('mkt-type')?.value || '';
  const rarity = document.getElementById('mkt-rarity')?.value || '';
  const sort   = document.getElementById('mkt-sort')?.value || 'price_asc';

  let url = `/market/?page=${_mktCurrentPage}&sort=${sort}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (type)   url += `&item_type=${type}`;
  if (rarity) url += `&rarity=${rarity}`;

  showLoading('mkt-table-wrap');
  try {
    const d = await api('GET', url);
    mktTotalPages = d.pages;
    renderMarketTable(d.listings, d.total);
    const pager = document.getElementById('mkt-pager');
    pager.style.display = d.total > 20 ? 'flex' : 'none';
    set('mkt-page-info', `${_mktCurrentPage} / ${d.pages}`);
    document.getElementById('mkt-prev').disabled = _mktCurrentPage <= 1;
    document.getElementById('mkt-next').disabled = _mktCurrentPage >= d.pages;
  } catch(e) { toast(e.message,'e'); }
}

function changeMktPage(dir) {
  _mktCurrentPage = Math.max(1, Math.min(mktTotalPages, _mktCurrentPage + dir));
  loadMarket();
}

function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => { _mktCurrentPage = 1; loadMarket(); }, 400);
}

function renderMarketTable(listings, total) {
  const wrap = document.getElementById('mkt-table-wrap');
  if (!listings.length) {
    wrap.innerHTML = `<div class="mkt-empty">Žádné nabídky na trhu${total===0?'.':' pro tento filtr.'}</div>`;
    return;
  }
  wrap.innerHTML = `
    <div style="font-size:.7rem;color:var(--text2);margin-bottom:6px;font-family:'Cinzel',serif">${total} nabídek celkem</div>
    <table class="mkt-table">
      <thead><tr>
        <th>Item</th><th>Rarity</th><th>Prodejce</th><th>Cena / ks</th><th>Ks</th><th></th>
      </tr></thead>
      <tbody>
        ${listings.map(l => {
          const rc = RARITY_COL[l.item?.rarity] || '#9d9d9d';
          const myChar = char && l.seller === char.name;
          return `<tr data-item="${JSON.stringify(l.item||{}).replace(/"/g,'&quot;')}" data-mkt-price="${l.price}">
            <td>
              <div class="mkt-item-cell">
                <div class="mkt-item-icon">${l.item?.icon||'📦'}</div>
                <div>
                  <div class="mkt-item-name" style="color:${rc}">${esc(l.item?.name||'?')}</div>
                  <div class="mkt-item-type">${l.item?.type||''}</div>
                </div>
              </div>
            </td>
            <td><span style="color:${rc};font-size:.72rem;font-family:'Cinzel',serif">${RARITY_CZ[l.item?.rarity]||l.item?.rarity||'?'}</span></td>
            <td class="mkt-seller">${esc(l.seller)}</td>
            <td class="mkt-price">${l.price.toLocaleString('cs')} G</td>
            <td style="color:var(--text2);font-size:.8rem">${l.quantity}</td>
            <td>${myChar
              ? `<button class="my-cancel-btn" onclick="cancelListing(${l.id})">✕ Zrušit</button>`
              : `<button class="mkt-buy-btn" onclick="buyListing(${l.id},'${esc(l.item?.name||'?')}',${l.price*l.quantity})">Koupit ${(l.price*l.quantity).toLocaleString('cs')} G</button>`
            }</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
  _registerTipContainer('mkt-table-wrap', 'tr[data-item]', row => {
    try {
      const item = JSON.parse(row.dataset.item.replace(/&quot;/g, '"'));
      if (!item?.name) return null;
      const price = parseInt(row.dataset.mktPrice) || item.sell_price || 0;
      return { item: { ...item, sell_price: price }, upgrade_level: 0, durability: 100 };
    } catch { return null; }
  });
}

async function buyListing(id, name, total) {
  if (!confirm(`Koupit "${name}" za ${total.toLocaleString('cs')} G?`)) return;
  try {
    const d = await api('POST', `/market/buy/${id}`);
    toast(d.message, 's', 4000);
    addAct(`🛒 Koupeno: ${name} za ${total} G`);
    await refreshChar();
    loadMarket();
    loadMyListings();
  } catch(e) { toast(e.message, 'e'); }
}

async function cancelListing(id) {
  try {
    const d = await api('DELETE', `/market/cancel/${id}`);
    toast(d.message, 'i');
    loadMarket();
    loadMyListings();
    await loadInventory();
  } catch(e) { toast(e.message, 'e'); }
}

async function loadMyListings() {
  try {
    const d = await api('GET', '/market/my-listings');
    const el = document.getElementById('my-listings');
    if (!d.listings.length) {
      el.innerHTML = '<div style="color:var(--text3);font-size:.76rem;font-style:italic">Žádné aktivní nabídky...</div>';
      return;
    }
    el.innerHTML = d.listings.map(l => `
      <div class="my-listing-row">
        <span style="font-size:1rem">${l.item?.icon||'📦'}</span>
        <span class="my-listing-name">${esc(l.item?.name||'?')}</span>
        <span class="my-listing-price">${l.price.toLocaleString('cs')} G</span>
        <button class="my-cancel-btn" onclick="cancelListing(${l.id})">✕</button>
      </div>`).join('');
  } catch(e) {}
}

function prepareSell(inv) {
  sellInvId = inv.id;
  const item = inv.item;
  const rc = RARITY_COL[item?.rarity] || '#9d9d9d';

  document.getElementById('sell-preview').classList.add('show');
  set('sip-icon', item?.icon || '📦');
  set('sip-name', item?.name || '?');
  document.getElementById('sip-rarity').textContent = RARITY_CZ[item?.rarity] || item?.rarity || '?';
  document.getElementById('sip-rarity').style.color = rc;

  const bonuses = Object.entries(item?.bonuses || {}).filter(([,v]) => v > 0);
  document.getElementById('sip-bonuses').innerHTML = bonuses.map(([k,v]) => `+${v} ${k.toUpperCase()}`).join('  ·  ');

  document.getElementById('sell-price').value = item?.sell_price ? item.sell_price * 3 : '';
  document.getElementById('sell-qty').value = 1;
  document.getElementById('sell-qty').max = inv.quantity;
  document.getElementById('sell-form').style.display = 'flex';
}

async function listOnMarket() {
  if (!sellInvId) return toast('Vyber item z inventáře.', 'e');
  const price = parseInt(document.getElementById('sell-price').value);
  const qty   = parseInt(document.getElementById('sell-qty').value);
  if (!price || price < 1) return toast('Zadej platnou cenu.', 'e');
  if (!qty   || qty < 1)   return toast('Zadej platné množství.', 'e');

  try {
    const d = await api('POST', '/market/list', { inv_item_id: sellInvId, quantity: qty, price });
    toast(d.message, 's', 4000);
    addAct(`📤 Vystaveno na trhu: ${price} G`);
    sellInvId = null;
    document.getElementById('sell-preview').classList.remove('show');
    document.getElementById('sell-form').style.display = 'none';
    await refreshChar();
    await loadInventory();
    loadMyListings();
    loadMarket();
  } catch(e) { toast(e.message, 'e'); }
}
