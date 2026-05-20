/**
 * NovaCart 个人中心交互
 *
 * 功能：个性化推荐、浏览历史、收藏夹、偏好设置
 */

const CATEGORY_EMOJI = { '手机':'📱','平板':'💻','耳机':'🎧','配件':'🔌','笔记本':'💻','显示器':'🖥','存储':'💾','穿戴':'⌚','无人机':'🛸','游戏机':'🎮' };

function getEmoji(cat) { return CATEGORY_EMOJI[cat] || '📦'; }
function formatPrice(p) { return '¥' + Number(p).toLocaleString('zh-CN'); }
function escapeHtml(text) { const d = document.createElement('div'); d.textContent = text; return d.innerHTML; }

// ==================== localStorage 工具 ====================
function getUserId() {
  let id = localStorage.getItem('userId');
  if (!id) { id = 'user_' + Math.random().toString(36).slice(2, 10); localStorage.setItem('userId', id); }
  return id;
}

function getFavorites() { try { return JSON.parse(localStorage.getItem('favorites') || '[]'); } catch { return []; } }
function saveFavorites(favs) { localStorage.setItem('favorites', JSON.stringify(favs)); }

function getHistory() { try { return JSON.parse(localStorage.getItem('viewHistory') || '[]'); } catch { return []; } }
function saveHistory(items) { localStorage.setItem('viewHistory', JSON.stringify(items.slice(0, 20))); }

function getRecommendHistory() { try { return JSON.parse(localStorage.getItem('recommendHistory') || '[]'); } catch { return []; } }
function saveRecommendHistory(items) { localStorage.setItem('recommendHistory', JSON.stringify(items.slice(0, 10))); }

function getPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem('userPrefs') || '{}');
    return { categories: p.categories || ['手机','耳机','平板'], minPrice: p.minPrice ?? 0, maxPrice: p.maxPrice ?? 10000 };
  } catch { return { categories: ['手机','耳机','平板'], minPrice: 0, maxPrice: 10000 }; }
}
function savePrefsToStorage(prefs) { localStorage.setItem('userPrefs', JSON.stringify(prefs)); }

// ==================== 用户信息 ====================
function initProfile() {
  const uid = getUserId();
  document.getElementById('profileId').textContent = uid.slice(0, 16);
  document.getElementById('profileName').textContent = '用户 ' + uid.slice(0, 6);

  document.getElementById('statViews').textContent = getHistory().length;
  document.getElementById('statFavorites').textContent = getFavorites().length;

  // 加载偏好设置
  const prefs = getPrefs();
  document.getElementById('prefMinPrice').value = prefs.minPrice;
  document.getElementById('prefMaxPrice').value = prefs.maxPrice;
  document.querySelectorAll('.pref-tag').forEach(btn => {
    btn.classList.toggle('active', prefs.categories.includes(btn.dataset.cat));
  });
}

// ==================== 偏好设置 ====================
function initPrefs() {
  document.querySelectorAll('.pref-tag').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
    });
  });

  document.getElementById('savePrefs').addEventListener('click', () => {
    const categories = [];
    document.querySelectorAll('.pref-tag.active').forEach(btn => categories.push(btn.dataset.cat));
    const minPrice = parseFloat(document.getElementById('prefMinPrice').value) || 0;
    const maxPrice = parseFloat(document.getElementById('prefMaxPrice').value) || 10000;
    savePrefsToStorage({ categories, minPrice, maxPrice });
    showToast('偏好已保存');
    loadPersonalRecs();
  });
}

// ==================== 个性化推荐 ====================
async function loadPersonalRecs() {
  const grid = document.getElementById('personalRecGrid');
  grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';

  try {
    const prefs = getPrefs();
    const params = new URLSearchParams({
      segment: 'personal',
      page: '1',
      page_size: '8'
    });
    if (prefs.categories.length > 0) {
      params.set('preferred_categories', prefs.categories.join(','));
    }

    let products = [];
    try {
      const data = await AppUI.fetchApiJson(`/api/v1/recommendations?${params.toString()}`);
      products = AppUI.normalizeProducts(data.items || []);
    } catch (error) {
      const resp = await AppUI.fetchJson('/api/v1/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: getUserId(),
          scene: 'personal',
          num_items: 8,
          context: {
            recent_views: prefs.categories,
            purchase_count_30d: 3,
            avg_order_amount: (prefs.minPrice + prefs.maxPrice) / 2
          }
        })
      });
      products = AppUI.normalizeProducts(resp.products || []);
    }
    renderProductGrid(grid, products, true);

    // 保存推荐历史
    if (products.length > 0) {
      const record = { time: new Date().toLocaleString(), count: products.length, items: products.slice(0, 3).map(p => p.name) };
      const history = getRecommendHistory();
      history.unshift(record);
      saveRecommendHistory(history);
      renderRecommendHistory();
    }
  } catch (e) {
    console.error('加载个性化推荐失败:', e);
    grid.innerHTML = '<div class="empty-state">加载失败，请稍后重试</div>';
  }
}

function renderProductGrid(container, products, showFavBtn) {
  const safeProducts = AppUI.normalizeProducts(products);
  if (!safeProducts || safeProducts.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无商品</div>';
    return;
  }

  const favs = getFavorites();
  container.innerHTML = safeProducts.map((product, idx) => {
    const emoji = getEmoji(product.category);
    const isFav = favs.some(f => f.product_id === product.product_id);
    const tags = (product.tags || []).slice(0, 2).map(tag => {
      let cls = ''; if (tag === '新品') cls = 'new'; else if (tag === '旗舰') cls = 'hot';
      return `<span class="product-tag ${cls}">${escapeHtml(tag)}</span>`;
    });

    return `
      <article class="product-card" data-product-id="${escapeHtml(product.product_id)}" style="animation: rise 500ms ease ${idx * 50}ms both">
        <div class="product-image">
          ${emoji}
          ${showFavBtn ? `<button class="fav-btn ${isFav ? 'favorited' : ''}" data-pid="${escapeHtml(product.product_id)}">${isFav ? '❤' : '♡'}</button>` : ''}
        </div>
        <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
        <div class="product-meta">
          <span class="product-category">${escapeHtml(product.category || '-')}</span>
        </div>
        <div class="product-price">${formatPrice(product.price)}</div>
        <div class="product-tags">${tags.join('')}</div>
      </article>
    `;
  }).join('');

  if (showFavBtn) {
    container.querySelectorAll('.fav-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFavorite(btn.dataset.pid, safeProducts, btn);
      });
    });
  }

  // 点击商品卡片加入浏览历史
  container.querySelectorAll('.product-card').forEach(card => {
    card.addEventListener('click', () => {
      const name = card.querySelector('.product-name').textContent;
      addToHistory(name);
      if (card.dataset.productId) {
        window.location.href = `/product/${encodeURIComponent(card.dataset.productId)}`;
      }
    });
  });
}

// ==================== 收藏 ====================
function toggleFavorite(pid, products, btn) {
  let favs = getFavorites();
  const existing = favs.find(f => f.product_id === pid);

  if (existing) {
    favs = favs.filter(f => f.product_id !== pid);
    btn.classList.remove('favorited');
    btn.textContent = '♡';
  } else {
    const product = products.find(p => p.product_id === pid);
    if (product) {
      favs.push({ product_id: pid, name: product.name, category: product.category, price: product.price, time: new Date().toISOString() });
      btn.classList.add('favorited');
      btn.textContent = '❤';
    }
  }

  saveFavorites(favs);
  document.getElementById('statFavorites').textContent = favs.length;
  renderFavorites();
}

function renderFavorites() {
  const grid = document.getElementById('favoritesGrid');
  const favs = getFavorites();
  if (favs.length === 0) {
    grid.innerHTML = '<div class="empty-state">还没有收藏商品，去首页逛逛吧</div>';
    return;
  }

  grid.innerHTML = favs.map((fav, idx) => `
    <article class="product-card" data-product-id="${escapeHtml(fav.product_id || '')}" style="animation: rise 500ms ease ${idx * 50}ms both">
      <div class="product-image">${getEmoji(fav.category)}</div>
      <h3 class="product-name" title="${escapeHtml(fav.name)}">${escapeHtml(fav.name)}</h3>
      <div class="product-meta"><span class="product-category">${escapeHtml(fav.category || '-')}</span></div>
      <div class="product-price">${formatPrice(fav.price)}</div>
    </article>
  `).join('');

  grid.querySelectorAll('.product-card[data-product-id]').forEach(card => {
    card.addEventListener('click', () => {
      if (card.dataset.productId) {
        window.location.href = `/product/${encodeURIComponent(card.dataset.productId)}`;
      }
    });
  });
}

// ==================== 浏览历史 ====================
function addToHistory(name) {
  const history = getHistory();
  const filtered = history.filter(h => h.name !== name);
  filtered.unshift({ name, time: new Date().toLocaleString() });
  saveHistory(filtered);
  renderHistory();
  document.getElementById('statViews').textContent = filtered.length;
}

function renderHistory() {
  const list = document.getElementById('historyList');
  const history = getHistory();
  if (history.length === 0) {
    list.innerHTML = '<div class="empty-state">暂无浏览记录</div>';
    return;
  }

  list.innerHTML = history.map(h => `
    <div class="history-item">
      <div class="hi-left"><span class="hi-icon">👁</span><span class="hi-name">${escapeHtml(h.name)}</span></div>
      <span class="hi-meta">${h.time}</span>
    </div>
  `).join('');
}

// ==================== 推荐历史 ====================
function renderRecommendHistory() {
  const list = document.getElementById('recommendHistory');
  const history = getRecommendHistory();
  if (history.length === 0) {
    list.innerHTML = '<div class="empty-state">暂无推荐记录</div>';
    return;
  }

  list.innerHTML = history.map(h => `
    <div class="history-item">
      <div class="hi-left"><span class="hi-icon">📋</span><span class="hi-name">推荐了 ${h.count} 个商品</span></div>
      <span class="hi-meta">${h.time}</span>
    </div>
  `).join('');
}

// ==================== Toast ====================
function showToast(msg) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position:fixed;bottom:2rem;right:2rem;z-index:1000;display:flex;flex-direction:column;gap:0.5rem';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.style.cssText = 'background:white;padding:0.8rem 1.2rem;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.15);border-left:4px solid var(--accent);animation:slideIn 300ms ease;font-size:0.9rem;color:var(--text)';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.animation = 'slideIn 300ms ease reverse'; setTimeout(() => toast.remove(), 300); }, 2000);
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  initProfile();
  initPrefs();
  loadPersonalRecs();
  renderHistory();
  renderFavorites();
  renderRecommendHistory();

  document.getElementById('refreshPersonal').addEventListener('click', loadPersonalRecs);
  document.getElementById('clearHistory').addEventListener('click', () => {
    localStorage.removeItem('viewHistory');
    renderHistory();
    document.getElementById('statViews').textContent = '0';
    showToast('浏览记录已清除');
  });
});
