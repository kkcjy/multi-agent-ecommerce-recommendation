/**
 * NovaCart 分类页交互
 */

const CATEGORY_MAP = {
  '手机': '📱', '平板': '💻', '耳机': '🎧', '配件': '🔌',
  '笔记本': '💻', '显示器': '🖥', '存储': '💾', '穿戴': '⌚',
  '无人机': '🛸', '游戏机': '🎮'
};

const State = {
  currentCategory: 'all',
  currentSort: 'default',
  currentTag: null,
  priceMin: null,
  priceMax: null,
  allProducts: [],
  filteredProducts: [],
  page: 1,
  pageSize: 12,
  total: 0,
  query: ''
};

function formatPrice(price) {
  return '¥' + Number(price).toLocaleString('zh-CN');
}

function getEmoji(category) {
  return CATEGORY_MAP[category] || '📦';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ==================== 数据加载 ====================
async function loadProducts() {
  const grid = document.getElementById('categoryProductGrid');
  grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';

  try {
    await loadCategories();
    await loadCategoryPage();
  } catch (error) {
    console.error('加载商品失败:', error);
    grid.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
  }
}

async function loadCategories() {
  try {
    const data = await AppUI.fetchApiJson('/api/v1/categories');
    buildCategoryNav(data.items || []);
  } catch (error) {
    const data = await AppUI.fetchApiJson('/api/v1/search?page=1&page_size=200');
    State.allProducts = AppUI.normalizeProducts(data.items || []);
    buildCategoryNav(State.allProducts);
  }
}

async function loadCategoryPage() {
  const grid = document.getElementById('categoryProductGrid');
  grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';

  const params = new URLSearchParams({
    page: String(State.page),
    page_size: String(State.pageSize),
    sort: State.currentSort
  });

  if (State.currentTag) {
    params.set('tag', State.currentTag);
  }
  if (State.priceMin !== null) {
    params.set('min_price', String(State.priceMin));
  }
  if (State.priceMax !== null) {
    params.set('max_price', String(State.priceMax));
  }
  if (State.query) {
    params.set('q', State.query);
  }

  const endpoint = State.currentCategory === 'all'
    ? `/api/v1/search?${params.toString()}`
    : `/api/v1/category/${encodeURIComponent(State.currentCategory)}?${params.toString()}`;

  try {
    const data = await AppUI.fetchApiJson(endpoint);
    const products = AppUI.normalizeProducts(data.items || []);
    State.filteredProducts = products;
    State.total = data.total !== undefined ? data.total : products.length;
    renderProducts(products);
    renderPagination();
  } catch (error) {
    console.error('加载商品失败:', error);
    if (State.allProducts.length > 0) {
      applyFilters();
      return;
    }
    grid.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
  }
}

// ==================== 分类导航 ====================
function buildCategoryNav(products) {
  const nav = document.getElementById('categoryNav');
  const list = Array.isArray(products) ? products : [];
  let categories = [];

  if (list.length > 0 && (list[0].id || list[0].name) && list[0].count !== undefined) {
    categories = list.map(item => ({
      id: item.id || item.name,
      name: item.name || item.id,
      count: item.count || 0
    }));
  } else {
    const byCategory = {};
    list.forEach(p => {
      const cat = p.category;
      if (!byCategory[cat]) {
        byCategory[cat] = 0;
      }
      byCategory[cat] += 1;
    });
    categories = Object.keys(byCategory).map(cat => ({
      id: cat,
      name: cat,
      count: byCategory[cat]
    }));
  }

  categories.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));

  const items = categories.map(cat => {
    return `<button class="cat-nav-item" data-category="${escapeHtml(cat.id)}">${CATEGORY_MAP[cat.id] || '📦'} ${escapeHtml(cat.name)} <small style="color:var(--muted)">(${cat.count})</small></button>`;
  });
  nav.innerHTML = '<button class="cat-nav-item active" data-category="all">全部商品</button>' + items.join('');

  nav.querySelectorAll('.cat-nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      nav.querySelectorAll('.cat-nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.currentCategory = btn.dataset.category;
      State.query = '';
      State.page = 1;
      applyFilters();
      document.getElementById('currentCategory').textContent = btn.dataset.category === 'all' ? '全部商品' : btn.dataset.category;
    });
  });
}

// ==================== 筛选与排序 ====================
function applyFilters() {
  if (!State.allProducts || State.allProducts.length === 0) {
    loadCategoryPage();
    return;
  }

  let products = [...State.allProducts];

  if (State.currentCategory !== 'all') {
    products = products.filter(p => p.category === State.currentCategory);
  }

  if (State.currentTag) {
    products = products.filter(p => p.tags && p.tags.includes(State.currentTag));
  }

  if (State.priceMin !== null) {
    products = products.filter(p => p.price >= State.priceMin);
  }
  if (State.priceMax !== null) {
    products = products.filter(p => p.price <= State.priceMax);
  }

  switch (State.currentSort) {
    case 'price-asc': products.sort((a, b) => a.price - b.price); break;
    case 'price-desc': products.sort((a, b) => b.price - a.price); break;
    case 'stock': products.sort((a, b) => b.stock - a.stock); break;
    default: break;
  }

  State.filteredProducts = products;
  State.total = products.length;
  renderPage();
}

function renderPage() {
  const start = (State.page - 1) * State.pageSize;
  const pageProducts = State.filteredProducts.slice(start, start + State.pageSize);
  renderProducts(pageProducts);
  renderPagination();
}

function renderProducts(products) {
  const grid = document.getElementById('categoryProductGrid');
  const safeProducts = AppUI.normalizeProducts(products);
  if (!safeProducts || safeProducts.length === 0) {
    grid.innerHTML = '<div class="empty-state">暂无符合条件的商品</div>';
    return;
  }

  grid.innerHTML = safeProducts.map((product, index) => {
    const emoji = getEmoji(product.category);
    const tags = [];
    if (product.tags) {
      product.tags.slice(0, 3).forEach(tag => {
        let cls = '';
        if (tag === '新品') cls = 'new';
        else if (tag === '旗舰') cls = 'hot';
        tags.push(`<span class="product-tag ${cls}">${escapeHtml(tag)}</span>`);
      });
    }

    return `
      <article class="product-card" style="animation: rise 500ms ease ${index * 40}ms both">
        <div class="product-image">${emoji}</div>
        <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
        <div class="product-meta">
          <span class="product-category">${escapeHtml(product.category || '-')}</span>
          <span class="product-stock">库存 ${product.stock ?? '-'}</span>
        </div>
        <div class="product-price-wrapper">
          <span class="product-price">${formatPrice(product.price)}</span>
        </div>
        <div class="product-tags">${tags.join('')}</div>
      </article>
    `;
  }).join('');
}

function renderPagination() {
  const totalPages = Math.ceil(State.total / State.pageSize);
  const container = document.getElementById('pagination');
  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = '';
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="page-btn ${i === State.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
  }
  container.innerHTML = html;

  container.querySelectorAll('.page-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      State.page = parseInt(btn.dataset.page);
      if (State.allProducts && State.allProducts.length > 0) {
        renderPage();
      } else {
        loadCategoryPage();
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

// ==================== 事件绑定 ====================
function initFilters() {
  document.getElementById('applyPriceFilter').addEventListener('click', () => {
    const min = parseFloat(document.getElementById('minPrice').value) || null;
    const max = parseFloat(document.getElementById('maxPrice').value) || null;
    State.priceMin = min;
    State.priceMax = max;
    State.page = 1;
    applyFilters();
  });

  document.querySelectorAll('.quick-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const isActive = tag.classList.contains('active');
      document.querySelectorAll('.quick-tag').forEach(t => t.classList.remove('active'));
      if (isActive) {
        State.currentTag = null;
      } else {
        tag.classList.add('active');
        State.currentTag = tag.dataset.tag;
      }
      State.page = 1;
      applyFilters();
    });
  });

  document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.currentSort = btn.dataset.sort;
      State.page = 1;
      applyFilters();
    });
  });
}

function initSearch() {
  const input = document.getElementById('headerSearch');
  const btn = document.getElementById('headerSearchBtn');
  if (!input || !btn) return;

  const search = () => {
    const query = input.value.trim().toLowerCase();
    if (query) {
      State.currentCategory = 'all';
      State.query = query;
      document.querySelectorAll('.cat-nav-item').forEach(b => b.classList.remove('active'));
      const allBtn = document.querySelector('.cat-nav-item[data-category="all"]');
      if (allBtn) allBtn.classList.add('active');
      document.getElementById('currentCategory').textContent = `搜索：${input.value}`;
      State.page = 1;
      applyFilters();
    }
  };

  btn.addEventListener('click', search);
  input.addEventListener('keypress', e => { if (e.key === 'Enter') search(); });
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  loadProducts();
  initFilters();
  initSearch();
});
