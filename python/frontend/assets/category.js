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
  pageSize: 12
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
    const response = await fetch('/api/v1/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'category_browser',
        scene: 'personal',
        num_items: 50,
        context: {}
      })
    });
    const data = await response.json();
    State.allProducts = data.products || [];
    buildCategoryNav(State.allProducts);
    applyFilters();
  } catch (error) {
    console.error('加载商品失败:', error);
    grid.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
  }
}

// ==================== 分类导航 ====================
function buildCategoryNav(products) {
  const nav = document.getElementById('categoryNav');
  const categories = [...new Set(products.map(p => p.category))].sort();
  const items = categories.map(cat => {
    const count = products.filter(p => p.category === cat).length;
    return `<button class="cat-nav-item" data-category="${escapeHtml(cat)}">${CATEGORY_MAP[cat] || '📦'} ${escapeHtml(cat)} <small style="color:var(--muted)">(${count})</small></button>`;
  });
  nav.innerHTML = '<button class="cat-nav-item active" data-category="all">全部商品</button>' + items.join('');

  nav.querySelectorAll('.cat-nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      nav.querySelectorAll('.cat-nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      State.currentCategory = btn.dataset.category;
      State.page = 1;
      applyFilters();
      document.getElementById('currentCategory').textContent = btn.dataset.category === 'all' ? '全部商品' : btn.dataset.category;
    });
  });
}

// ==================== 筛选与排序 ====================
function applyFilters() {
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
  if (!products || products.length === 0) {
    grid.innerHTML = '<div class="empty-state">暂无符合条件的商品</div>';
    return;
  }

  grid.innerHTML = products.map((product, index) => {
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
      <article class="product-card" data-product-id="${escapeHtml(product.product_id)}" style="animation: rise 500ms ease ${index * 40}ms both">
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

  grid.querySelectorAll('.product-card[data-product-id]').forEach(card => {
    card.addEventListener('click', () => {
      window.location.href = `/product/${encodeURIComponent(card.dataset.productId)}`;
    });
  });
}

function renderPagination() {
  const totalPages = Math.ceil(State.filteredProducts.length / State.pageSize);
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
      renderPage();
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
      State.filteredProducts = State.allProducts.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.category.toLowerCase().includes(query) ||
        (p.tags || []).some(t => t.toLowerCase().includes(query))
      );
      document.querySelectorAll('.cat-nav-item').forEach(b => b.classList.remove('active'));
      const allBtn = document.querySelector('.cat-nav-item[data-category="all"]');
      if (allBtn) allBtn.classList.add('active');
      document.getElementById('currentCategory').textContent = `搜索：${input.value}`;
      State.page = 1;
      renderPage();
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
