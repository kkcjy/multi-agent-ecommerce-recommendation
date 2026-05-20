/**
 * NovaCart 首页交互逻辑
 * 负责人 1：信息架构 & 视觉系统
 *
 * 功能:
 * - 分层次推荐流加载（你想搜 / 站内热门 / 个性化 / 新品）
 * - 楼层导航联动
 * - 商品卡片渲染
 * - 筛选器功能
 */

// ==================== 状态管理 ====================
const AppState = {
  currentSegment: 'all',
  currentSort: 'sales',
  selectedCategory: 'all',
  priceRange: { min: null, max: null },
  loadingSegments: new Set(),
  segments: {
    intent: [],
    hot: [],
    personal: [],
    new: []
  }
};

// ==================== 工具函数 ====================
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 300ms ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function formatPrice(price) {
  return '¥' + Number(price).toLocaleString('zh-CN');
}

function getProductEmoji(category) {
  const emojis = {
    '手机': '📱',
    '平板': '💻',
    '耳机': '🎧',
    '配件': '🔌',
    '手表': '⌚',
    '电脑': '💻',
  };
  return emojis[category] || '📦';
}

// ==================== 数据加载 ====================
async function loadSegmentData(segment, numItems = 8) {
  if (AppState.loadingSegments.has(segment)) return;

  const gridElement = document.getElementById(`${segment}Grid`);
  if (!gridElement) return;

  AppState.loadingSegments.add(segment);
  showSkeleton(gridElement);

  try {
    const response = await fetch('/api/v1/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: getUserId(),
        scene: segment,
        num_items: numItems,
        context: { recent_views: getRecentViews() }
      })
    });

    const data = await response.json();

    if (data.products && data.products.length > 0) {
      AppState.segments[segment] = data.products;
      renderProducts(gridElement, data.products, segment);

      if (segment === 'personal') {
        updateRecentViews(data.products);
      }
    } else {
      gridElement.innerHTML = '<div class="empty-state">暂无推荐商品</div>';
    }
  } catch (error) {
    console.error('加载推荐数据失败:', error);
    showToast('加载失败，请稍后重试', 'error');
    gridElement.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
  } finally {
    AppState.loadingSegments.delete(segment);
  }
}

async function loadAllSegments() {
  // 先加载 personal，将类目数据写入 localStorage
  // 再并行加载其余 segment，确保它们有 recent_views 可用
  await loadSegmentData('personal', 8);
  await Promise.all([
    loadSegmentData('intent', 4),
    loadSegmentData('hot', 8),
    loadSegmentData('new', 4)
  ]);
}

// ==================== 渲染函数 ====================
function showSkeleton(container) {
  container.innerHTML = `
    <div class="loading-skeleton">
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    </div>
  `;
}

function renderProducts(container, products, segment) {
  if (!products || products.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无商品</div>';
    return;
  }

  const html = products.map((product, index) => {
    const emoji = getProductEmoji(product.category);
    const explain = product.explain || {};
    const tags = buildProductTags(product, segment);

    return `
      <article class="product-card" data-product-id="${escapeHtml(product.product_id)}" style="animation: rise 500ms ease ${index * 50}ms both">
        <div class="product-image">
          ${emoji}
          ${tags._badge ? `<span class="product-badge">${tags._badge}</span>` : ''}
        </div>
        <h3 class="product-name" title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
        <div class="product-meta">
          <span class="product-category">${escapeHtml(product.category || '-')}</span>
          <span class="product-stock">库存${product.stock ?? '-'}</span>
        </div>
        <div class="product-price-wrapper">
          <span class="product-price">${formatPrice(product.price)}</span>
          ${product.originalPrice ? `<span class="product-original-price">${formatPrice(product.originalPrice)}</span>` : ''}
        </div>
        <div class="product-tags">
          ${tags.map(tag => `<span class="product-tag ${tag.class}">${tag.text}</span>`).join('')}
        </div>
        ${explain.recall_source ? `
          <div class="product-reason" title="推荐原因">
            <small>💡 ${translateRecallSource(explain.recall_source)}</small>
          </div>
        ` : ''}
      </article>
    `;
  }).join('');

  container.innerHTML = html;

  container.querySelectorAll('.product-card[data-product-id]').forEach(card => {
    card.addEventListener('click', () => {
      window.location.href = `/product/${encodeURIComponent(card.dataset.productId)}`;
    });
  });
}

function buildProductTags(product, segment) {
  const tags = [];
  const explain = product.explain || {};

  // 根据 segment 添加标签
  if (segment === 'hot') {
    tags.push({ text: '热销', class: 'hot' });
  } else if (segment === 'new') {
    tags.push({ text: '新品', class: 'new' });
  }

  // 根据价格添加促销标签
  if (product.price < 200) {
    tags.push({ text: '性价比', class: 'promo' });
  }

  // 根据 tags 数组添加
  if (product.tags && Array.isArray(product.tags)) {
    product.tags.slice(0, 2).forEach(tag => {
      tags.push({ text: tag, class: '' });
    });
  }

  tags._badge = segment === 'hot' ? 'HOT' : segment === 'new' ? 'NEW' : '';
  return tags;
}

function translateRecallSource(source) {
  const map = {
    'hot': '热门商品',
    'category': '类目匹配',
    'new': '新品推荐',
    'vector': '智能推荐',
    'collaborative': '相似选择'
  };
  return map[source] || source;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ==================== 用户相关 ====================
function getUserId() {
  let userId = localStorage.getItem('userId');
  if (!userId) {
    userId = 'user_' + Date.now().toString(36);
    localStorage.setItem('userId', userId);
  }
  return userId;
}

function getRecentViews() {
  const views = localStorage.getItem('recentViews');
  return views ? JSON.parse(views) : [];
}

function updateRecentViews(products) {
  const views = getRecentViews();
  const newViews = products.slice(0, 5).map(p => p.category || p.name).filter(Boolean);

  // 合并并去重
  const merged = [...new Set([...newViews, ...views])].slice(0, 10);
  localStorage.setItem('recentViews', JSON.stringify(merged));

  renderRecentViews(merged);
}

function renderRecentViews(views) {
  const container = document.getElementById('recentViews');
  if (!container) return;

  if (!views || views.length === 0) {
    container.innerHTML = '<div class="empty-state">暂无浏览记录</div>';
    return;
  }

  container.innerHTML = views.map(view => `
    <div class="recent-view-item">
      <span>👁</span>
      <span>${escapeHtml(view)}</span>
    </div>
  `).join('');
}

// ==================== 楼层导航 ====================
function initFloorNav() {
  const nav = document.getElementById('floorNav');
  const sections = document.querySelectorAll('.recommend-section');

  if (!nav) return;

  const items = nav.querySelectorAll('.floor-item');

  // 点击滚动
  items.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = item.getAttribute('href').substring(1);
      const target = document.getElementById(targetId);
      if (target) {
        const offsetTop = target.offsetTop - 120;
        window.scrollTo({ top: offsetTop, behavior: 'smooth' });
      }
    });
  });

  // 滚动监听高亮
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        items.forEach(item => {
          item.classList.toggle('active', item.getAttribute('href') === `#${id}`);
        });
      }
    });
  }, { rootMargin: '-150px 0px -60% 0px', threshold: 0 });

  sections.forEach(section => observer.observe(section));
}

// ==================== 筛选功能 ====================
function initFilters() {
  const categoryTags = document.querySelectorAll('.category-tag');
  const applyBtn = document.getElementById('applyFilter');
  const minPriceInput = document.getElementById('minPrice');
  const maxPriceInput = document.getElementById('maxPrice');

  categoryTags.forEach(tag => {
    tag.addEventListener('click', () => {
      categoryTags.forEach(t => t.classList.remove('active'));
      tag.classList.add('active');
      AppState.selectedCategory = tag.dataset.category;
    });
  });

  if (applyBtn) {
    applyBtn.addEventListener('click', () => {
      const minPrice = parseFloat(minPriceInput.value) || null;
      const maxPrice = parseFloat(maxPriceInput.value) || null;

      AppState.priceRange = { min: minPrice, max: maxPrice };
      applyFilters();
      showToast('筛选已应用', 'success');
    });
  }
}

function applyFilters() {
  const { selectedCategory, priceRange, segments } = AppState;

  Object.keys(segments).forEach(key => {
    const grid = document.getElementById(`${key}Grid`);
    if (!grid) return;

    let filtered = segments[key];

    // 类目筛选
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(p => p.category === selectedCategory);
    }

    // 价格筛选
    if (priceRange.min !== null) {
      filtered = filtered.filter(p => p.price >= priceRange.min);
    }
    if (priceRange.max !== null) {
      filtered = filtered.filter(p => p.price <= priceRange.max);
    }

    renderProducts(grid, filtered, key);
  });
}

// ==================== 排序功能 ====================
function initSortTabs() {
  const sortTabs = document.querySelectorAll('.sort-tab');

  sortTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const parent = tab.closest('.sort-tabs');
      parent.querySelectorAll('.sort-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const sortType = tab.dataset.sort;
      AppState.currentSort = sortType;

      // 对热门商品进行排序
      const hotGrid = document.getElementById('hotGrid');
      if (hotGrid && AppState.segments.hot.length > 0) {
        let sorted = [...AppState.segments.hot];

        switch (sortType) {
          case 'price':
            sorted.sort((a, b) => a.price - b.price);
            break;
          case 'new':
            sorted.sort((a, b) => b.stock - a.stock); // 用库存模拟新品
            break;
          case 'sales':
          default:
            sorted.sort((a, b) => b.price * b.stock - a.price * a.stock); // 用价格*库存模拟销量
            break;
        }

        renderProducts(hotGrid, sorted, 'hot');
      }
    });
  });
}

// ==================== 刷新功能 ====================
function initRefreshButtons() {
  const buttons = document.querySelectorAll('.refresh-btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const segment = btn.dataset.segment;
      if (segment) {
        loadSegmentData(segment, 8);
        showToast('已刷新', 'success');
      }
    });
  });

  // Banner 刷新按钮
  const bannerBtn = document.getElementById('refreshRecommend');
  if (bannerBtn) {
    bannerBtn.addEventListener('click', () => {
      loadAllSegments();
      showToast('推荐已更新', 'success');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
}

// ==================== 搜索功能 ====================
function initSearch() {
  const searchInput = document.getElementById('headerSearch');
  const searchBtn = document.getElementById('headerSearchBtn');

  if (!searchInput || !searchBtn) return;

  const performSearch = () => {
    const query = searchInput.value.trim();
    if (query) {
      // 保存到最近搜索
      const searches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
      if (!searches.includes(query)) {
        searches.unshift(query);
        localStorage.setItem('recentSearches', JSON.stringify(searches.slice(0, 10)));
      }
      showToast(`搜索：${query}`, 'info');
      // TODO: 跳转到搜索结果页
    }
  };

  searchBtn.addEventListener('click', performSearch);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  console.log('NovaCart Home initialized');

  // 加载数据
  loadAllSegments();

  // 初始化交互
  initFloorNav();
  initFilters();
  initSortTabs();
  initRefreshButtons();
  initSearch();

  // 渲染最近浏览
  renderRecentViews(getRecentViews());

  // 用户画像（模拟）
  const userProfile = document.getElementById('userProfile');
  if (userProfile) {
    userProfile.innerHTML = `
      <div class="profile-info">
        <div class="profile-stat">
          <span class="stat-label">用户 ID</span>
          <span class="stat-value">${getUserId().slice(0, 12)}</span>
        </div>
        <div class="profile-stat">
          <span class="stat-label">偏好</span>
          <span class="stat-value">数码/配件</span>
        </div>
      </div>
    `;
  }
});
