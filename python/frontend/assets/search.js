/**
 * NovaCart 搜索页交互
 */

const CATEGORY_EMOJI = {
  '手机': '📱', '平板': '💻', '耳机': '🎧', '配件': '🔌',
  '笔记本': '💻', '显示器': '🖥', '存储': '💾', '穿戴': '⌚',
  '无人机': '🛸', '游戏机': '🎮'
};

let allProducts = [];

function formatPrice(price) { return '¥' + Number(price).toLocaleString('zh-CN'); }
function getEmoji(cat) { return CATEGORY_EMOJI[cat] || '📦'; }
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ==================== 搜索历史 ====================
function getSearches() {
  try { return JSON.parse(localStorage.getItem('recentSearches') || '[]'); }
  catch { return []; }
}

function saveSearch(query) {
  const searches = getSearches().filter(s => s !== query);
  searches.unshift(query);
  localStorage.setItem('recentSearches', JSON.stringify(searches.slice(0, 10)));
  renderRecentSearches();
}

function clearSearches() {
  localStorage.removeItem('recentSearches');
  renderRecentSearches();
}

function renderRecentSearches() {
  const container = document.getElementById('recentSearches');
  const clearBtn = document.getElementById('clearSearches');
  const searches = getSearches();

  if (searches.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无搜索记录</div>';
    if (clearBtn) clearBtn.style.display = 'none';
    return;
  }

  if (clearBtn) clearBtn.style.display = 'block';
  container.innerHTML = searches.map(q => `
    <div class="recent-search-item" data-query="${escapeHtml(q)}">
      <span>🕐 ${escapeHtml(q)}</span>
      <button class="remove-search" data-query="${escapeHtml(q)}">✕</button>
    </div>
  `).join('');

  container.querySelectorAll('.recent-search-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('remove-search')) return;
      const q = item.dataset.query;
      document.getElementById('mainSearch').value = q;
      performSearch(q);
    });
  });

  container.querySelectorAll('.remove-search').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const q = btn.dataset.query;
      const searches = getSearches().filter(s => s !== q);
      localStorage.setItem('recentSearches', JSON.stringify(searches));
      renderRecentSearches();
    });
  });
}

// ==================== 搜索执行 ====================
function performSearch(query) {
  const q = query.trim().toLowerCase();
  const grid = document.getElementById('searchResultGrid');
  const count = document.getElementById('resultsCount');

  if (!q) {
    grid.innerHTML = '<div class="empty-state search-empty"><span style="font-size:3rem">🔍</span><p style="margin-top:1rem">输入关键词开始搜索</p></div>';
    count.textContent = '';
    return;
  }

  saveSearch(q);

  const results = allProducts.filter(p =>
    p.name.toLowerCase().includes(q) ||
    p.category.toLowerCase().includes(q) ||
    (p.tags || []).some(t => t.toLowerCase().includes(q)) ||
    (p.brand || '').toLowerCase().includes(q)
  );

  count.textContent = `共 ${results.length} 个结果`;

  if (results.length === 0) {
    grid.innerHTML = '<div class="empty-state search-empty"><span style="font-size:3rem">😕</span><p style="margin-top:1rem">未找到匹配的商品</p><p style="color:var(--muted);font-size:0.85rem">试试其他关键词</p></div>';
    return;
  }

  grid.innerHTML = results.map((product, index) => {
    const emoji = getEmoji(product.category);
    const tags = (product.tags || []).slice(0, 3).map(tag => {
      let cls = '';
      if (tag === '新品') cls = 'new';
      else if (tag === '旗舰') cls = 'hot';
      return `<span class="product-tag ${cls}">${escapeHtml(tag)}</span>`;
    });

    return `
      <article class="product-card" style="animation: rise 500ms ease ${index * 40}ms both">
        <div class="product-image">${emoji}</div>
        <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
        <div class="product-meta">
          <span class="product-category">${escapeHtml(product.category || '-')}</span>
          <span class="product-stock">库存 ${product.stock ?? '-'}</span>
        </div>
        <div class="product-price">${formatPrice(product.price)}</div>
        <div class="product-tags">${tags.join('')}</div>
      </article>
    `;
  }).join('');
}

// ==================== 热门搜索 ====================
function initHotSearches() {
  document.querySelectorAll('.hot-search-item').forEach(item => {
    item.addEventListener('click', () => {
      const q = item.dataset.query;
      document.getElementById('mainSearch').value = q;
      performSearch(q);
    });
  });
}

// ==================== 搜索建议 ====================
function updateSuggestions(query) {
  const container = document.getElementById('searchSuggestions');
  const q = query.trim().toLowerCase();
  if (!q || allProducts.length === 0) {
    container.innerHTML = '';
    return;
  }

  const matches = allProducts
    .filter(p => p.name.toLowerCase().includes(q))
    .slice(0, 5);

  if (matches.length === 0) { container.innerHTML = ''; return; }

  container.innerHTML = matches.map(p =>
    `<button class="suggestion-item">${getEmoji(p.category)} ${escapeHtml(p.name)}</button>`
  ).join('');

  container.querySelectorAll('.suggestion-item').forEach((btn, i) => {
    btn.addEventListener('click', () => {
      document.getElementById('mainSearch').value = matches[i].name;
      performSearch(matches[i].name);
    });
  });
}

// ==================== 数据加载 ====================
async function loadProducts() {
  try {
    const resp = await fetch('/api/v1/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'search_browser', scene: 'personal', num_items: 50, context: {} })
    });
    const data = await resp.json();
    allProducts = data.products || [];
  } catch (e) {
    console.error('加载商品数据失败:', e);
  }
}

// ==================== 事件 ====================
function initSearchEvents() {
  const input = document.getElementById('mainSearch');
  const btn = document.getElementById('mainSearchBtn');

  btn.addEventListener('click', () => performSearch(input.value));
  input.addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(input.value); });
  input.addEventListener('input', () => updateSuggestions(input.value));

  document.getElementById('clearSearches').addEventListener('click', clearSearches);

  // URL query 参数预填搜索
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  if (q) {
    input.value = q;
    performSearch(q);
  }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  loadProducts().then(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('q')) {
      performSearch(params.get('q'));
    }
  });
  renderRecentSearches();
  initHotSearches();
  initSearchEvents();
});
