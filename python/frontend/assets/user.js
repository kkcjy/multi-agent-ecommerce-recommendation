/**
 * NovaCart 个人中心 — 全部交互逻辑
 * 功能：订单管理 / 收藏夹 / 浏览历史 / 个性化推荐 / 收货地址 / 优惠券 / 资料编辑
 */

// ==================== 工具函数 ====================
function $(id) { return document.getElementById(id); }
function $$(sel, ctx) { return (ctx || document).querySelectorAll(sel); }
function escapeHtml(text) { const d = document.createElement('div'); d.textContent = text; return d.innerHTML; }
function formatPrice(p) { return '¥' + Number(p).toLocaleString('zh-CN'); }
function nowISO() { return new Date().toISOString(); }
function uid() { return 'id_' + Math.random().toString(36).slice(2, 10); }
function getEmoji(cat) {
  const m = {'手机':'📱','平板':'💻','耳机':'🎧','配件':'🔌','笔记本':'💻','显示器':'🖥','存储':'💾','穿戴':'⌚','无人机':'🛸','游戏机':'🎮'};
  return m[cat] || '📦';
}

// ==================== Toast ====================
function showToast(msg, type) {
  type = type || '';
  var c = $('toastContainer');
  var t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function() { t.style.animation = 'toastIn 300ms ease reverse'; setTimeout(function() { t.remove(); }, 300); }, 2200);
}

// ==================== localStorage 工具 ====================
function getUserId() {
  var id = localStorage.getItem('userId');
  if (!id) { id = 'user_' + Math.random().toString(36).slice(2, 10); localStorage.setItem('userId', id); }
  return id;
}

function loadJSON(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch(e) { return fallback; }
}

function saveJSON(key, val) { localStorage.setItem(key, JSON.stringify(val)); }

// ==================== Mock 数据生成 ====================
var CATEGORIES = ['手机','耳机','平板','配件','笔记本','穿戴'];
var PRODUCT_POOL = [
  {name:'iPhone 16 Pro Max', cat:'手机', price:9999, emoji:'📱'},
  {name:'Samsung Galaxy S25', cat:'手机', price:8999, emoji:'📱'},
  {name:'AirPods Pro 3', cat:'耳机', price:1899, emoji:'🎧'},
  {name:'Sony WH-1000XM6', cat:'耳机', price:2499, emoji:'🎧'},
  {name:'iPad Pro M4', cat:'平板', price:6799, emoji:'💻'},
  {name:'MacBook Air 15', cat:'笔记本', price:10999, emoji:'💻'},
  {name:'Apple Watch Ultra 3', cat:'穿戴', price:5999, emoji:'⌚'},
  {name:'小米 15 Ultra', cat:'手机', price:6499, emoji:'📱'},
  {name:'华为 Mate 70 Pro', cat:'手机', price:7999, emoji:'📱'},
  {name:'DJI Mini 4 Pro', cat:'无人机', price:4788, emoji:'🛸'},
  {name:'PS5 Pro', cat:'游戏机', price:4999, emoji:'🎮'},
  {name:'三星 T9 2TB', cat:'存储', price:1599, emoji:'💾'},
  {name:'Anker 充电器 100W', cat:'配件', price:299, emoji:'🔌'},
  {name:'罗技 MX Master 4', cat:'配件', price:799, emoji:'🔌'},
  {name:'Dell 4K 显示器', cat:'显示器', price:3299, emoji:'🖥'},
];

function randomProduct() {
  return PRODUCT_POOL[Math.floor(Math.random() * PRODUCT_POOL.length)];
}

function initMockOrders() {
  if (loadJSON('orders', null)) return;
  var orders = [];
  var statuses = ['completed','completed','pending_recv','pending_ship','pending_pay','completed','pending_recv','cancelled'];
  for (var i = 0; i < statuses.length; i++) {
    var p = randomProduct();
    var days = Math.floor(Math.random() * 30) + 1;
    var t = new Date(Date.now() - days * 86400000);
    orders.push({
      order_id: 'NC' + (20260501001 + i),
      status: statuses[i],
      product: p,
      quantity: Math.floor(Math.random() * 2) + 1,
      total: p.price * (Math.floor(Math.random() * 2) + 1),
      time: t.toISOString(),
      timeStr: t.toLocaleDateString('zh-CN') + ' ' + t.toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'})
    });
  }
  saveJSON('orders', orders);
}

function initMockCoupons() {
  if (loadJSON('coupons', null)) return;
  var coupons = [
    {id:uid(), type:'discount', amount:30, name:'满300减30', desc:'全场通用', minSpend:300, expire:'2026-12-31', used:false},
    {id:uid(), type:'discount', amount:50, name:'满500减50', desc:'数码品类', minSpend:500, expire:'2026-06-30', used:false},
    {id:uid(), type:'full', amount:20, name:'新人立减20', desc:'首单可用', minSpend:0, expire:'2026-07-15', used:false},
    {id:uid(), type:'discount', amount:100, name:'满1000减100', desc:'笔记本/手机', minSpend:1000, expire:'2026-05-30', used:true},
  ];
  saveJSON('coupons', coupons);
}

// ==================== 用户资料 ====================
function getProfile() {
  return loadJSON('profile', { avatar:'👤', name:'' });
}
function saveProfile(p) { saveJSON('profile', p); }

function initProfile() {
  var profile = getProfile();
  var uid = getUserId();
  $('profileAvatar').textContent = profile.avatar || '👤';
  $('profileName').textContent = profile.name || ('用户 ' + uid.slice(0, 6));
  $('profileId').textContent = uid.slice(0, 16);
  updateProfileStats();
}

function updateProfileStats() {
  var orders = loadJSON('orders', []);
  var favs = loadJSON('favorites', []);
  var history = loadJSON('viewHistory', []);
  $('statOrders').textContent = orders.length;
  $('statFavorites').textContent = favs.length;
  $('statHistory').textContent = history.length;

  // 会员等级
  var total = orders.filter(function(o) { return o.status === 'completed'; }).length;
  var level = total >= 5 ? '钻石会员' : total >= 3 ? '黄金会员' : total >= 1 ? '白银会员' : '普通会员';
  $('profileLevel').textContent = level;
}

// ==================== 资料编辑弹窗 ====================
function initProfileModal() {
  var profile = getProfile();
  $('editProfileBtn').addEventListener('click', function() {
    $('profileNameInput').value = profile.name || '';
    $('profileModal').classList.add('open');
    $$('.avatar-option').forEach(function(btn) {
      btn.classList.toggle('selected', btn.dataset.avatar === profile.avatar);
    });
  });

  $('closeProfileModal').addEventListener('click', function() {
    $('profileModal').classList.remove('open');
  });

  $('avatarEditBtn').addEventListener('click', function() {
    $('profileModal').classList.add('open');
  });

  $$('.avatar-option').forEach(function(btn) {
    btn.addEventListener('click', function() {
      $$('.avatar-option').forEach(function(b) { b.classList.remove('selected'); });
      btn.classList.add('selected');
    });
  });

  $('saveProfileBtn').addEventListener('click', function() {
    var selected = document.querySelector('.avatar-option.selected');
    var avatar = selected ? selected.dataset.avatar : '👤';
    var name = $('profileNameInput').value.trim() || ('用户 ' + getUserId().slice(0, 6));
    profile.avatar = avatar;
    profile.name = name;
    saveProfile(profile);
    $('profileAvatar').textContent = avatar;
    $('profileName').textContent = name;
    $('profileModal').classList.remove('open');
    showToast('资料已保存', 'success');
  });

  // 点击遮罩关闭
  $('profileModal').addEventListener('click', function(e) {
    if (e.target === $('profileModal')) { $('profileModal').classList.remove('open'); }
  });
}

// ==================== 资产 ====================
function updateAssets() {
  var coupons = loadJSON('coupons', []);
  var unused = coupons.filter(function(c) { return !c.used; });
  $('couponCount').textContent = unused.length;
  $('pointsBalance').textContent = (unused.length * 120 + 80);
  $('balanceAmount').textContent = formatPrice(unused.length * 15 + 5);
}

// ==================== 内容区 Tab 切换 ====================
function initContentTabs() {
  $$('.content-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      var tabName = tab.dataset.tab;
      $$('.content-tab').forEach(function(t) { t.classList.remove('active'); });
      tab.classList.add('active');
      $$('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
      $('panel-' + tabName).classList.add('active');

      if (tabName === 'recommend') loadRecommendations();
      if (tabName === 'history') renderHistory();
      if (tabName === 'favorites') renderFavorites();
      if (tabName === 'orders') renderOrders('all');
    });
  });
}

// ==================== 订单管理 ====================
var currentOrderStatus = 'all';

function initOrders() {
  initMockOrders();

  // 状态子 tab
  $$('.status-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      $$('.status-tab').forEach(function(t) { t.classList.remove('active'); });
      tab.classList.add('active');
      currentOrderStatus = tab.dataset.status;
      renderOrders(currentOrderStatus);
    });
  });
}

function renderOrders(statusFilter) {
  var orders = loadJSON('orders', []);
  var filtered = statusFilter === 'all' ? orders : orders.filter(function(o) { return o.status === statusFilter; });

  var list = $('orderList');
  if (filtered.length === 0) {
    list.innerHTML = '<div class="empty-state"><span class="empty-icon">📋</span><p>暂无订单</p><a href="/home" class="empty-link">去逛逛</a></div>';
    return;
  }

  var statusMap = {
    pending_pay:  '待付款',
    pending_ship: '待发货',
    pending_recv: '待收货',
    completed:    '已完成',
    cancelled:    '已取消'
  };

  list.innerHTML = filtered.map(function(order) {
    var p = order.product;
    var actions = '';
    if (order.status === 'pending_pay') {
      actions = '<button class="order-action-btn secondary" data-action="cancel" data-oid="' + order.order_id + '">取消</button>' +
                '<button class="order-action-btn primary" data-action="pay" data-oid="' + order.order_id + '">去支付</button>';
    } else if (order.status === 'pending_ship') {
      actions = '<button class="order-action-btn secondary" data-action="remind" data-oid="' + order.order_id + '">提醒发货</button>';
    } else if (order.status === 'pending_recv') {
      actions = '<button class="order-action-btn primary" data-action="confirm" data-oid="' + order.order_id + '">确认收货</button>';
    } else if (order.status === 'completed') {
      actions = '<button class="order-action-btn secondary" data-action="reorder" data-oid="' + order.order_id + '">再次购买</button>' +
                '<button class="order-action-btn secondary" data-action="review" data-oid="' + order.order_id + '">评价</button>';
    } else if (order.status === 'cancelled') {
      actions = '<span style="font-size:0.8rem;color:var(--muted)">订单已取消</span>';
    }

    return '<div class="order-card">' +
      '<div class="order-header">' +
        '<span class="order-no">订单号：' + order.order_id + '</span>' +
        '<span class="order-status ' + order.status + '">' + (statusMap[order.status] || order.status) + '</span>' +
      '</div>' +
      '<div class="order-body">' +
        '<div class="order-product-icon">' + (p.emoji || getEmoji(p.cat)) + '</div>' +
        '<div class="order-product-info">' +
          '<div class="order-product-name">' + escapeHtml(p.name) + '</div>' +
          '<div class="order-product-meta">×' + order.quantity + '　' + order.timeStr + '</div>' +
        '</div>' +
        '<div class="order-product-price">' + formatPrice(order.total) + '</div>' +
      '</div>' +
      '<div class="order-footer">' +
        '<div class="order-total">共 <strong>' + order.quantity + '</strong> 件商品　合计 <strong>' + formatPrice(order.total) + '</strong></div>' +
        '<div class="order-actions">' + actions + '</div>' +
      '</div>' +
    '</div>';
  }).join('');

  // 绑定订单操作按钮
  bindOrderActions();
  updateProfileStats();
}

function bindOrderActions() {
  $$('.order-action-btn', $('orderList')).forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      var action = btn.dataset.action;
      var oid = btn.dataset.oid;
      var orders = loadJSON('orders', []);
      var order = orders.find(function(o) { return o.order_id === oid; });
      if (!order) return;

      switch(action) {
        case 'pay':
          order.status = 'pending_ship';
          showToast('支付成功！已提交发货', 'success');
          break;
        case 'cancel':
          if (confirm('确定取消该订单吗？')) {
            order.status = 'cancelled';
            showToast('订单已取消');
          }
          break;
        case 'confirm':
          order.status = 'completed';
          showToast('已确认收货', 'success');
          break;
        case 'reorder':
          var newOrder = JSON.parse(JSON.stringify(order));
          newOrder.order_id = 'NC' + (20260501001 + orders.length + 1);
          newOrder.status = 'pending_pay';
          newOrder.time = nowISO();
          newOrder.timeStr = new Date().toLocaleDateString('zh-CN');
          orders.unshift(newOrder);
          saveJSON('orders', orders);
          showToast('已重新下单', 'success');
          break;
        case 'remind':
          showToast('已提醒卖家发货');
          break;
        case 'review':
          showToast('评价功能开发中');
          break;
        default: break;
      }
      saveJSON('orders', orders);
      renderOrders(currentOrderStatus);
    });
  });
}

// ==================== 收藏夹 ====================
function getFavorites() { return loadJSON('favorites', []); }

function toggleFavorite(product) {
  var favs = getFavorites();
  var idx = favs.findIndex(function(f) { return f.product_id === product.product_id; });
  if (idx >= 0) {
    favs.splice(idx, 1);
    showToast('已取消收藏');
  } else {
    favs.push({
      product_id: product.product_id,
      name: product.name,
      category: product.category,
      price: product.price,
      emoji: getEmoji(product.category),
      time: nowISO()
    });
    showToast('已加入收藏', 'success');
  }
  saveJSON('favorites', favs);
  updateProfileStats();
  updateAssets();
  return idx < 0; // true if favorited
}

function isFavorited(pid) {
  return getFavorites().some(function(f) { return f.product_id === pid; });
}

function renderFavorites() {
  var favs = getFavorites();
  var grid = $('favoritesGrid');
  $('favCount').textContent = '共 ' + favs.length + ' 件商品';

  if (favs.length === 0) {
    grid.innerHTML = '<div class="empty-state"><span class="empty-icon">❤️</span><p>还没有收藏商品</p><a href="/home" class="empty-link">去首页逛逛</a></div>';
    return;
  }

  grid.innerHTML = favs.map(function(fav) {
    return '<article class="product-card">' +
      '<div class="product-image">' + (fav.emoji || getEmoji(fav.category)) +
        '<button class="fav-btn favorited" data-pid="' + fav.product_id + '">❤</button>' +
      '</div>' +
      '<h3 class="product-name" title="' + escapeHtml(fav.name) + '">' + escapeHtml(fav.name) + '</h3>' +
      '<div class="product-meta"><span class="product-category">' + escapeHtml(fav.category || '-') + '</span></div>' +
      '<div class="product-price">' + formatPrice(fav.price) + '</div>' +
    '</article>';
  }).join('');

  // 取消收藏按钮
  $$('.fav-btn', grid).forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      var pid = btn.dataset.pid;
      var favs = getFavorites();
      var idx = favs.findIndex(function(f) { return f.product_id === pid; });
      if (idx >= 0) { favs.splice(idx, 1); saveJSON('favorites', favs); }
      renderFavorites();
      updateProfileStats();
      updateAssets();
      showToast('已取消收藏');
    });
  });
}

// ==================== 浏览历史 ====================
function renderHistory() {
  var history = loadJSON('viewHistory', []);
  $('historyCount').textContent = '共 ' + history.length + ' 条记录';

  if (history.length === 0) {
    $('historyTimeline').innerHTML = '<div class="empty-state"><span class="empty-icon">👁️</span><p>暂无浏览记录</p></div>';
    return;
  }

  // 按日期分组
  var groups = {};
  history.forEach(function(item) {
    var day = item.time ? item.time.slice(0, 10) : '未知日期';
    if (!groups[day]) groups[day] = [];
    groups[day].push(item);
  });

  var days = Object.keys(groups).sort().reverse();
  var html = '';
  days.forEach(function(day) {
    html += '<div class="history-day"><div class="history-day-label">' + day + '</div><div class="history-day-items">';
    groups[day].forEach(function(item) {
      var emoji = item.emoji || getEmoji(item.category || '');
      html += '<div class="history-item">' +
        '<div class="history-item-emoji">' + emoji + '</div>' +
        '<div class="history-item-info">' +
          '<div class="history-item-name">' + escapeHtml(item.name) + '</div>' +
          '<div class="history-item-meta">' + escapeHtml(item.category || '') + ' · ' + formatPrice(item.price || 0) + '</div>' +
        '</div>' +
        '<div class="history-item-time">' + (item.timeStr || '') + '</div>' +
      '</div>';
    });
    html += '</div></div>';
  });

  $('historyTimeline').innerHTML = html;
}

// ==================== 个性化推荐 ====================
async function loadRecommendations() {
  var grid = $('recommendGrid');
  grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';

  try {
    var resp = await fetch('/api/v1/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: getUserId(),
        scene: 'personal',
        num_items: 8,
        context: { recent_views: (loadJSON('viewHistory', [])).slice(0, 5).map(function(h) { return h.category || h.name; }) }
      })
    });
    var data = await resp.json();
    var products = data.products || [];

    if (products.length === 0) {
      grid.innerHTML = '<div class="empty-state"><span class="empty-icon">✨</span><p>暂无推荐商品</p></div>';
      return;
    }

    renderProductGrid(grid, products, true);
  } catch(e) {
    console.error('加载推荐失败:', e);
    grid.innerHTML = '<div class="empty-state"><span class="empty-icon">⚠️</span><p>加载失败，请稍后重试</p></div>';
  }
}

function renderProductGrid(container, products, showFav) {
  if (!products || products.length === 0) {
    container.innerHTML = '<div class="empty-state"><span class="empty-icon">📦</span><p>暂无商品</p></div>';
    return;
  }

  container.innerHTML = products.map(function(product, idx) {
    var emoji = product.emoji || getEmoji(product.category);
    var isFav = isFavorited(product.product_id);
    var tags = (product.tags || []).slice(0, 2).map(function(tag) {
      var cls = tag === '新品' ? 'new' : tag === '旗舰' ? 'hot' : '';
      return '<span class="product-tag ' + cls + '">' + escapeHtml(tag) + '</span>';
    });

    return '<article class="product-card" style="animation: rise 500ms ease ' + (idx * 50) + 'ms both">' +
      '<div class="product-image">' + emoji +
        (showFav ? '<button class="fav-btn ' + (isFav ? 'favorited' : '') + '" data-pid="' + escapeHtml(product.product_id) + '">' + (isFav ? '❤' : '♡') + '</button>' : '') +
      '</div>' +
      '<h3 class="product-name" title="' + escapeHtml(product.name) + '">' + escapeHtml(product.name) + '</h3>' +
      '<div class="product-meta"><span class="product-category">' + escapeHtml(product.category || '-') + '</span></div>' +
      '<div class="product-price">' + formatPrice(product.price) + '</div>' +
      '<div class="product-tags">' + tags.join('') + '</div>' +
    '</article>';
  }).join('');

  // 收藏按钮
  if (showFav) {
    $$('.fav-btn', container).forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var pid = btn.dataset.pid;
        var product = products.find(function(p) { return p.product_id === pid; });
        if (!product) return;
        var favored = toggleFavorite(product);
        btn.classList.toggle('favorited', favored);
        btn.textContent = favored ? '❤' : '♡';
      });
    });
  }

  // 点击加入历史
  $$('.product-card', container).forEach(function(card) {
    card.addEventListener('click', function() {
      var name = card.querySelector('.product-name').textContent;
      var cat = card.querySelector('.product-category').textContent;
      var priceText = card.querySelector('.product-price').textContent;
      addToHistory(name, cat, parseFloat(priceText.replace('¥', '').replace(/,/g, '')));
    });
  });
}

function addToHistory(name, category, price) {
  var history = loadJSON('viewHistory', []);
  history = history.filter(function(h) { return h.name !== name; });
  var now = new Date();
  history.unshift({
    name: name,
    category: category || '',
    price: price || 0,
    emoji: getEmoji(category),
    time: nowISO(),
    timeStr: now.toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'})
  });
  if (history.length > 50) history = history.slice(0, 50);
  saveJSON('viewHistory', history);
  updateProfileStats();
}

// ==================== 收货地址 ====================
function getAddresses() { return loadJSON('addresses', []); }

function renderAddressList() {
  var addrs = getAddresses();
  var list = $('addressList');
  if (addrs.length === 0) {
    list.innerHTML = '<div class="empty-state">暂无地址，请在下方添加</div>';
    return;
  }
  list.innerHTML = addrs.map(function(addr, i) {
    return '<div class="address-item' + (addr.isDefault ? ' default' : '') + '">' +
      '<div class="address-info">' +
        '<span class="addr-name">' + escapeHtml(addr.name) + '</span>' +
        '<span class="addr-phone">' + escapeHtml(addr.phone) + '</span>' +
        (addr.isDefault ? '<span class="addr-tag">默认</span>' : '') +
        '<div class="addr-full">' + escapeHtml(addr.province + addr.city + addr.district + ' ' + addr.detail) + '</div>' +
      '</div>' +
      '<div class="address-actions">' +
        '<button class="addr-action-btn" data-action="edit" data-idx="' + i + '">编辑</button>' +
        '<button class="addr-action-btn danger" data-action="delete" data-idx="' + i + '">删除</button>' +
      '</div>' +
    '</div>';
  }).join('');

  bindAddressActions();
}

function bindAddressActions() {
  $$('.addr-action-btn', $('addressList')).forEach(function(btn) {
    btn.addEventListener('click', function() {
      var action = btn.dataset.action;
      var idx = parseInt(btn.dataset.idx);
      var addrs = getAddresses();

      if (action === 'delete') {
        if (confirm('确定删除该地址吗？')) {
          addrs.splice(idx, 1);
          saveJSON('addresses', addrs);
          renderAddressList();
          showToast('地址已删除');
        }
      } else if (action === 'edit') {
        fillAddressForm(addrs[idx], idx);
      }
    });
  });
}

function fillAddressForm(addr, idx) {
  $('addrId').value = idx !== undefined ? idx : '';
  $('addrName').value = addr.name || '';
  $('addrPhone').value = addr.phone || '';
  $('addrProvince').value = addr.province || '';
  $('addrCity').value = addr.city || '';
  $('addrDistrict').value = addr.district || '';
  $('addrDetail').value = addr.detail || '';
  $('addrDefault').checked = addr.isDefault || false;
}

function initAddressModal() {
  $('addressBtn').addEventListener('click', function() {
    $('addrId').value = '';
    $('addressForm').reset();
    renderAddressList();
    $('addressModal').classList.add('open');
  });

  $('closeAddressModal').addEventListener('click', function() {
    $('addressModal').classList.remove('open');
  });

  $('addressModal').addEventListener('click', function(e) {
    if (e.target === $('addressModal')) { $('addressModal').classList.remove('open'); }
  });

  $('addressForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var addrs = getAddresses();
    var isDefault = $('addrDefault').checked;
    var addrData = {
      id: uid(),
      name: $('addrName').value.trim(),
      phone: $('addrPhone').value.trim(),
      province: $('addrProvince').value.trim(),
      city: $('addrCity').value.trim(),
      district: $('addrDistrict').value.trim(),
      detail: $('addrDetail').value.trim(),
      isDefault: isDefault
    };

    if (!addrData.name || !addrData.phone || !addrData.detail) {
      showToast('请填写完整信息', 'error');
      return;
    }

    var editIdx = $('addrId').value;
    if (editIdx !== '') {
      addrs[parseInt(editIdx)] = addrData;
    } else {
      if (isDefault) {
        addrs.forEach(function(a) { a.isDefault = false; });
      }
      addrs.push(addrData);
    }

    saveJSON('addresses', addrs);
    $('addressForm').reset();
    $('addrId').value = '';
    renderAddressList();
    showToast('地址已保存', 'success');
  });
}

// ==================== 优惠券弹窗 ====================
function initCouponModal() {
  $('couponBtn').addEventListener('click', function() {
    renderCoupons();
    $('couponModal').classList.add('open');
  });
  $('closeCouponModal').addEventListener('click', function() {
    $('couponModal').classList.remove('open');
  });
  $('couponModal').addEventListener('click', function(e) {
    if (e.target === $('couponModal')) { $('couponModal').classList.remove('open'); }
  });
}

function renderCoupons() {
  var coupons = loadJSON('coupons', []);
  var list = $('couponList');
  if (coupons.length === 0) {
    list.innerHTML = '<div class="empty-state">暂无优惠券</div>';
    return;
  }
  list.innerHTML = coupons.map(function(c) {
    return '<div class="coupon-card' + (c.used ? ' used' : '') + '">' +
      '<div class="coupon-left ' + c.type + '">' +
        '<span class="coupon-amount">' + (c.type === 'full' ? '¥' : '') + c.amount + (c.type === 'discount' ? '' : '') + '</span>' +
        '<span class="coupon-unit">' + (c.type === 'discount' ? '元' : '立减') + '</span>' +
      '</div>' +
      '<div class="coupon-right">' +
        '<span class="coupon-name">' + escapeHtml(c.name) + '</span>' +
        '<span class="coupon-desc">' + escapeHtml(c.desc) + (c.minSpend > 0 ? ' · 满' + c.minSpend + '可用' : '') + '</span>' +
        '<span class="coupon-expire">有效期至 ' + c.expire + (c.used ? ' (已使用)' : '') + '</span>' +
      '</div>' +
    '</div>';
  }).join('');
}

// ==================== 按钮事件绑定 ====================
function initButtons() {
  // 收藏清空
  $('clearFavs').addEventListener('click', function() {
    if (confirm('确定清空所有收藏吗？')) {
      saveJSON('favorites', []);
      renderFavorites();
      updateProfileStats();
      updateAssets();
      showToast('已清空收藏');
    }
  });

  // 历史清空
  $('clearHistory').addEventListener('click', function() {
    if (confirm('确定清空所有浏览记录吗？')) {
      saveJSON('viewHistory', []);
      renderHistory();
      updateProfileStats();
      showToast('浏览记录已清空');
    }
  });

  // 刷新推荐
  $('refreshRec').addEventListener('click', function() {
    loadRecommendations();
    showToast('推荐已刷新', 'success');
  });

  // 安全设置
  $('securityBtn').addEventListener('click', function() {
    showToast('安全设置功能开发中');
  });

  // 资产点击
  $$('.asset-item').forEach(function(item, i) {
    item.addEventListener('click', function() {
      if (i === 0) { $('couponBtn').click(); }
      else if (i === 1) { showToast('积分商城开发中'); }
      else { showToast('余额功能开发中'); }
    });
  });

  // 统计点击
  $('statOrders').parentElement.addEventListener('click', function() {
    $$('.content-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelector('.content-tab[data-tab="orders"]').classList.add('active');
    $$('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
    $('panel-orders').classList.add('active');
    renderOrders('all');
  });
  $('statFavorites').parentElement.addEventListener('click', function() {
    $$('.content-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelector('.content-tab[data-tab="favorites"]').classList.add('active');
    $$('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
    $('panel-favorites').classList.add('active');
    renderFavorites();
  });
  $('statHistory').parentElement.addEventListener('click', function() {
    $$('.content-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelector('.content-tab[data-tab="history"]').classList.add('active');
    $$('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
    $('panel-history').classList.add('active');
    renderHistory();
  });
}

// ==================== 初始化入口 ====================
document.addEventListener('DOMContentLoaded', function() {
  initMockOrders();
  initMockCoupons();
  initProfile();
  initProfileModal();
  initContentTabs();
  initOrders();
  initAddressModal();
  initCouponModal();
  initButtons();
  updateAssets();
  renderOrders('all');
});
