/**
 * NovaCart 搜索页交互
 */

const CATEGORY_EMOJI = {
  '手机': '📱', '平板': '💻', '耳机': '🎧', '配件': '🔌',
  '笔记本': '💻', '显示器': '🖥', '存储': '💾', '穿戴': '⌚',
  '无人机': '🛸', '游戏机': '🎮', '家电': '🧺', '智能家居': '🏠',
  '摄影': '📷', '办公设备': '🖨', '运动户外': '🏃'
};

let allProducts = [];
const HOT_SEARCH_FALLBACK = [
  { term: 'iPhone', emoji: '📱' },
  { term: '耳机', emoji: '🎧' },
  { term: '平板', emoji: '💻' },
  { term: '充电器', emoji: '🔌' },
  { term: '游戏', emoji: '🎮' },
  { term: '性价比', emoji: '💰' },
  { term: '空调', emoji: '🧺' },
  { term: '相机', emoji: '📷' },
  { term: '投影仪', emoji: '🖨' },
  { term: '露营', emoji: '🏃' }
];

function formatPrice(price) { return '¥' + Number(price).toLocaleString('zh-CN'); }
function getEmoji(cat) { return CATEGORY_EMOJI[cat] || '📦'; }
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderProductCards(grid, products) {
  grid.innerHTML = products.map((product, index) => {
    const emoji = getEmoji(product.category);
    const tags = (product.tags || []).slice(0, 3).map(tag => {
      let cls = '';
      if (tag === '新品') cls = 'new';
      else if (tag === '旗舰') cls = 'hot';
      return `<span class="product-tag ${cls}">${escapeHtml(tag)}</span>`;
    });
    const productId = product.product_id || product.id || '';

    return `
      <article class="product-card" data-product-id="${escapeHtml(productId)}" style="animation: rise 500ms ease ${index * 40}ms both">
        <div class="product-image">
          <img src="${escapeHtml(product.image_url || '')}" alt="${escapeHtml(product.name)}" loading="lazy"
               onerror="this.style.display='none';var s=this.nextElementSibling;if(s&&s.classList.contains('product-emoji'))s.style.display=''"
               ${!product.image_url ? ' style="display:none"' : ''} />
          <span class="product-emoji"${product.image_url ? ' style="display:none"' : ''}>${emoji}</span>
        </div>
        <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
        <div class="product-meta">
          <span class="product-category">${escapeHtml(product.category || '-')}</span>
          <span class="product-sales">已售 ${Math.max(product.sales || 0, (product.stock || 0) * 3, 99)}+</span>
        </div>
        <div class="product-meta">
          <span class="product-rating">${AppUI.ratingStars(product.rating || 4.8)} ${(product.rating || 4.8).toFixed(1)}</span>
          <span>评价 ${product.review_count || Math.max(20, Math.floor((product.sales || 300) / 12))}</span>
        </div>
        <div class="product-price-wrapper">
          <span class="product-price">${formatPrice(product.price)}</span>
          ${product.originalPrice ? `<span class="product-original-price">${formatPrice(product.originalPrice)}</span>` : `<span class="product-original-price">${formatPrice(Math.round(product.price * 1.08))}</span>`}
          <span class="save-badge">立减 ${formatPrice(Math.max(1, Math.round((product.originalPrice || product.price * 1.08) - product.price)))}</span>
        </div>
        <div class="product-tags">${tags.join('')}</div>
        ${AppUI.productCardActionsHtml(productId)}
      </article>
    `;
  }).join('');

  AppUI.bindCartButtons(products, grid);
  grid.querySelectorAll('.product-card[data-product-id]').forEach(card => {
    card.addEventListener('click', () => {
      if (card.dataset.productId) {
        window.location.href = `/product/${encodeURIComponent(card.dataset.productId)}`;
      }
    });
  });
}

// ==================== 搜索历史 ====================
function currentUserKey(name) {
  return `${name}_${localStorage.getItem('userId') || 'demo_tech'}`;
}

function getSearches() {
  try { return JSON.parse(localStorage.getItem(currentUserKey('recentSearches')) || '[]'); }
  catch { return []; }
}

function saveSearch(query) {
  const searches = getSearches().filter(s => s !== query);
  searches.unshift(query);
  localStorage.setItem(currentUserKey('recentSearches'), JSON.stringify(searches.slice(0, 10)));
  renderRecentSearches();
}

function clearSearches() {
  localStorage.removeItem(currentUserKey('recentSearches'));
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
const SEGMENT_TITLES = {
  intent: '你想搜',
  hot: '站内热门',
  personal: '个性化推荐'
};

const SearchState = {
  segment: 'intent',
  q: '',
  page: 1,
  pageSize: 12,
  total: 0
};

// per-segment page memory, simple page cache and scroll positions
SearchState.perSegmentPage = { intent: 1, hot: 1, personal: 1 };
SearchState.cache = {}; // key: `${segment}:${page}` -> { items, total }
SearchState.scrollPositions = {}; // segment -> scrollY

function updateSearchUrl(replace = true) {
  const params = new URLSearchParams();
  if (SearchState.q) params.set('q', SearchState.q);
  if (SearchState.segment && SearchState.segment !== 'intent') params.set('segment', SearchState.segment);
  if (SearchState.page && SearchState.page > 1) params.set('page', String(SearchState.page));
  if (SearchState.pageSize && SearchState.pageSize !== 12) params.set('page_size', String(SearchState.pageSize));
  const queryString = params.toString();
  const url = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
  if (replace) {
    window.history.replaceState(null, '', url);
  } else {
    window.history.pushState(null, '', url);
  }
}

function setSegmentActive(segment) {
  const prev = SearchState.segment;
  // save current page and scroll for previous segment
  if (prev && prev !== segment) {
    SearchState.perSegmentPage[prev] = SearchState.page || 1;
    try { SearchState.scrollPositions[prev] = window.scrollY || 0; } catch (e) { /* noop */ }
  }

  // set active segment and restore its page if we have one
  SearchState.segment = segment;
  SearchState.page = SearchState.perSegmentPage[segment] || 1;

  document.querySelectorAll('.segment-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.segment === segment);
  });
  document.getElementById('segmentTabs').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // restore scroll position for the segment if recorded
  const pos = SearchState.scrollPositions[segment];
  if (pos !== undefined) {
    setTimeout(() => { try { window.scrollTo(0, pos); } catch (e) {} }, 60);
  }
}

function renderSearchHeader() {
  const header = document.getElementById('resultsHeader');
  const label = document.getElementById('segmentLabel');
  if (label) {
    label.textContent = SearchState.q ? `${SEGMENT_TITLES[SearchState.segment]} - ${SearchState.q}` : SEGMENT_TITLES[SearchState.segment];
  }
}

function renderSearchPagination() {
  const container = document.getElementById('searchPagination');
  const totalPages = Math.ceil(SearchState.total / SearchState.pageSize);
  if (!container) return;
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  const pages = [];
  for (let i = 1; i <= totalPages; i += 1) {
    pages.push(`<button class="page-btn ${i === SearchState.page ? 'active' : ''}" data-page="${i}">${i}</button>`);
  }
  container.innerHTML = pages.join('');
  container.querySelectorAll('.page-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const nextPage = Number(btn.dataset.page);
      if (nextPage === SearchState.page) return;
      SearchState.page = nextPage;
      loadSearchSegment();
    });
  });
}

function renderSearchResults(products, total) {
  const grid = document.getElementById('searchResultGrid');
  const count = document.getElementById('resultsCount');

  SearchState.total = total !== undefined ? total : products.length;
  renderSearchHeader();
  updateSearchUrl();
  count.textContent = `共 ${SearchState.total} 个结果`;

  if (!products || products.length === 0) {
    grid.innerHTML = '<div class="empty-state search-empty"><span style="font-size:3rem">😕</span><p style="margin-top:1rem">未找到匹配的商品</p><p style="color:var(--muted);font-size:0.85rem">试试其他关键词</p></div>';
    document.getElementById('searchPagination').innerHTML = '';
    return;
  }

  renderProductCards(grid, products);
  renderSearchPagination();
}

async function loadSearchSegment() {
  const grid = document.getElementById('searchResultGrid');
  const count = document.getElementById('resultsCount');
  grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';
  count.textContent = '';
  renderSearchHeader();

  try {
    // remember current page for this segment
    SearchState.perSegmentPage[SearchState.segment] = SearchState.page || 1;

    // check simple cache first
    const cacheKey = `${SearchState.segment}:${SearchState.q || ''}:${SearchState.page}`;
    const cached = SearchState.cache[cacheKey];
    if (cached) {
      renderSearchResults(cached.items, cached.total);
      return;
    }

    let data;
    if (SearchState.segment === 'intent' && SearchState.q) {
      const params = new URLSearchParams({
        q: SearchState.q,
        page: String(SearchState.page),
        page_size: String(SearchState.pageSize)
      });
      data = await AppUI.fetchApiJson(`/api/v1/search?${params.toString()}`);
    } else {
      const params = new URLSearchParams({
        segment: SearchState.segment,
        page: String(SearchState.page),
        page_size: String(SearchState.pageSize)
      });
      const recent = getSearches();
      if (SearchState.segment === 'intent' && recent.length > 0) {
        params.set('recent_views', recent.join(','));
      }
      if (SearchState.segment === 'personal' && recent.length > 0) {
        params.set('preferred_categories', recent.join(','));
      }
      data = await AppUI.fetchApiJson(`/api/v1/recommendations?${params.toString()}`);
    }

    const results = AppUI.normalizeProducts(data.items || []);
    const total = data.total !== undefined ? data.total : results.length;
    // cache the page results for quick return
    try { SearchState.cache[cacheKey] = { items: results, total }; } catch (e) { /* noop */ }
    renderSearchResults(results, total);
  } catch (error) {
    console.error('加载分层次结果失败:', error);
    if (SearchState.segment === 'intent' && SearchState.q && allProducts.length > 0) {
      const qLower = SearchState.q.toLowerCase();
      const results = allProducts.filter(p =>
        p.name.toLowerCase().includes(qLower) ||
        p.category.toLowerCase().includes(qLower) ||
        (p.tags || []).some(t => t.toLowerCase().includes(qLower)) ||
        (p.brand || '').toLowerCase().includes(qLower)
      );
      renderSearchResults(results, results.length);
      return;
    }
    const gridFallback = document.getElementById('searchResultGrid');
    gridFallback.innerHTML = '<div class="empty-state search-empty"><span style="font-size:3rem">⚠️</span><p style="margin-top:1rem">内容加载失败，请稍后重试</p></div>';
    document.getElementById('searchPagination').innerHTML = '';
  }
}

async function performSearch(query) {
  const qRaw = query.trim();
  if (!qRaw) {
    const grid = document.getElementById('searchResultGrid');
    grid.innerHTML = '<div class="empty-state search-empty"><span style="font-size:3rem">🔍</span><p style="margin-top:1rem">输入关键词开始搜索</p></div>';
    document.getElementById('resultsCount').textContent = '';
    return;
  }

  SearchState.q = qRaw;
  SearchState.segment = 'intent';
  SearchState.page = 1;
  saveSearch(qRaw);
  setSegmentActive('intent');
  await loadSearchSegment();
}

// ==================== 热门搜索 ====================
function renderHotSearches(items) {
  const container = document.getElementById('hotSearches');
  if (!container) return;
  const list = items && items.length ? items : HOT_SEARCH_FALLBACK;
  container.innerHTML = list.map(item => (
    `<button class="hot-search-item" data-query="${escapeHtml(item.term)}">${item.emoji || '🔥'} ${escapeHtml(item.term)}</button>`
  )).join('');

  container.querySelectorAll('.hot-search-item').forEach(item => {
    item.addEventListener('click', () => {
      const q = item.dataset.query;
      document.getElementById('mainSearch').value = q;
      performSearch(q);
    });
  });
}

async function loadHotSearches() {
  try {
    const data = await AppUI.fetchApiJson('/api/v1/search/hot');
    renderHotSearches(data.items || []);
  } catch (error) {
    renderHotSearches(HOT_SEARCH_FALLBACK);
  }
}

// ==================== 搜索建议 ====================
let suggestionTimer = null;

function updateSuggestions(query) {
  const container = document.getElementById('searchSuggestions');
  const q = query.trim();
  if (!q) {
    container.innerHTML = '';
    return;
  }

  if (suggestionTimer) {
    clearTimeout(suggestionTimer);
  }

  suggestionTimer = setTimeout(async () => {
    try {
      const data = await AppUI.fetchApiJson(`/api/v1/search/suggestions?q=${encodeURIComponent(q)}`);
      const items = data.items || [];
      if (items.length === 0) {
        container.innerHTML = '';
        return;
      }
      container.innerHTML = items.map(item =>
        `<button class="suggestion-item">${item.emoji || getEmoji(item.category)} ${escapeHtml(item.text)}</button>`
      ).join('');

      container.querySelectorAll('.suggestion-item').forEach((btn, i) => {
        btn.addEventListener('click', () => {
          document.getElementById('mainSearch').value = items[i].text;
          performSearch(items[i].text);
        });
      });
    } catch (error) {
      const qLower = q.toLowerCase();
      const matches = allProducts
        .filter(p => p.name.toLowerCase().includes(qLower))
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
  }, 220);
}

// ==================== 数据加载 ====================
async function loadProducts() {
  try {
    const data = await AppUI.fetchApiJson('/api/v1/search?page=1&page_size=200');
    allProducts = AppUI.normalizeProducts(data.items || []);
  } catch (e) {
    console.error('加载商品数据失败:', e);
  }
}

function parseSearchUrl() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q') || '';
  const segment = params.get('segment') || 'intent';
  const page = Number(params.get('page')) || 1;
  const pageSize = Number(params.get('page_size')) || 12;

  SearchState.q = q;
  SearchState.segment = ['intent', 'hot', 'personal'].includes(segment) ? segment : 'intent';
  SearchState.page = page;
  SearchState.pageSize = pageSize;
}

function initSegmentTabs() {
  document.querySelectorAll('.segment-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.segment;
      if (!target || SearchState.segment === target) return;
      setSegmentActive(target);
      loadSearchSegment();
    });
  });
}

// ==================== 事件 ====================
function initSearchEvents() {
  const input = document.getElementById('mainSearch');
  const btn = document.getElementById('mainSearchBtn');

  btn.addEventListener('click', () => performSearch(input.value));
  input.addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(input.value); });
  input.addEventListener('input', () => updateSuggestions(input.value));

  document.getElementById('clearSearches').addEventListener('click', clearSearches);
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', async () => {
  parseSearchUrl();
  const input = document.getElementById('mainSearch');
  if (input && SearchState.q) {
    input.value = SearchState.q;
  }

  initSegmentTabs();
  renderRecentSearches();
  loadHotSearches();
  await loadProducts();

  setSegmentActive(SearchState.segment);
  if (SearchState.q || SearchState.segment !== 'intent') {
    loadSearchSegment();
  }
  initSearchEvents();
});
