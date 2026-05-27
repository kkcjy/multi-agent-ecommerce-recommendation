const CartPage = {
  items: [],
  selected: new Set(),
};

function cartMoney(value) {
  return '¥' + Number(value || 0).toLocaleString('zh-CN');
}

function cartEsc(value) {
  return AppUI.escapeHtml(value ?? '');
}

function cartEmoji(category) {
  const map = { 手机:'📱', 平板:'💻', 耳机:'🎧', 配件:'🔌', 笔记本:'💻', 显示器:'🖥', 存储:'💾', 穿戴:'⌚' };
  return map[category] || '📦';
}

function loadCartItems() {
  CartPage.items = AppUI.getCart();
  CartPage.selected = new Set(CartPage.items.map(item => item.product_id + JSON.stringify(item.sku || {})));
}

function saveCartItems() {
  AppUI.saveCart(CartPage.items);
}

function itemKey(item) {
  return item.product_id + JSON.stringify(item.sku || {});
}

function renderCart() {
  const content = document.getElementById('cartContent');
  const summary = document.getElementById('cartSummary');
  const hint = document.getElementById('cartUserHint');
  if (hint) hint.textContent = `当前用户：${AppUI.getCurrentUserId()} · 购物车按用户隔离保存`;

  if (!CartPage.items.length) {
    content.innerHTML = `
      <div class="empty-state cart-empty">
        <div style="font-size:3rem">🛒</div>
        <h3>购物车空空如也</h3>
        <p>把喜欢的商品加入购物车，统一结算更方便。</p>
        <a class="cart-continue primary" href="/category">去逛逛吧 →</a>
      </div>
    `;
    summary.innerHTML = `
      <h3>结算信息</h3>
      <div class="cart-summary-line"><span>商品数量</span><strong>0 件</strong></div>
      <div class="cart-summary-line"><span>合计</span><strong>${cartMoney(0)}</strong></div>
      <button class="cart-checkout-btn" disabled>去结算</button>
    `;
    AppUI.updateCartBadge();
    return;
  }

  content.innerHTML = `
    <div class="cart-toolbar">
      <label><input type="checkbox" id="selectAllCart" ${CartPage.selected.size === CartPage.items.length ? 'checked' : ''} /> 全选</label>
      <button class="cart-clear-btn" id="clearCartBtn" type="button">清空购物车</button>
    </div>
    <div class="cart-list">
      ${CartPage.items.map((item, index) => renderCartItem(item, index)).join('')}
    </div>
  `;

  renderSummary();
  bindCartEvents();
  AppUI.updateCartBadge();
}

function renderCartItem(item, index) {
  const key = itemKey(item);
  const checked = CartPage.selected.has(key) ? 'checked' : '';
  const skuText = Object.values(item.sku || {}).filter(Boolean).join(' / ') || '官方标配';
  const price = Number(item.finalPrice || item.price || 0);
  const original = Number(item.originalPrice || 0);
  const qty = Math.max(1, Number(item.quantity || 1));
  return `
    <article class="cart-item" data-index="${index}">
      <label class="cart-select"><input type="checkbox" class="cart-select-input" data-index="${index}" ${checked} /></label>
      <a class="cart-item-img" href="/product/${encodeURIComponent(item.product_id)}">
        <img src="${cartEsc(item.image_url || '')}" alt="${cartEsc(item.name)}" onerror="this.outerHTML='<span class=&quot;cart-img-fallback&quot;>${cartEmoji(item.category)}</span>'" />
      </a>
      <div class="cart-item-info">
        <a class="cart-item-name" href="/product/${encodeURIComponent(item.product_id)}">${cartEsc(item.name)}</a>
        <div class="cart-item-meta">${cartEsc(item.brand || item.category || '-')} · ${cartEsc(skuText)}</div>
        <div class="product-rating">${AppUI.ratingStars(item.rating || 4.8)} <span>${Number(item.rating || 4.8).toFixed(1)}</span></div>
      </div>
      <div class="cart-item-price">
        <strong>${cartMoney(price)}</strong>
        ${original > price ? `<span class="product-original-price">${cartMoney(original)}</span>` : ''}
      </div>
      <div class="cart-qty-control">
        <button type="button" class="qty-minus" data-index="${index}">-</button>
        <input class="qty-input" data-index="${index}" value="${qty}" inputmode="numeric" />
        <button type="button" class="qty-plus" data-index="${index}">+</button>
      </div>
      <div class="cart-subtotal">${cartMoney(price * qty)}</div>
      <button class="cart-remove-btn" type="button" data-index="${index}">删除</button>
    </article>
  `;
}

function selectedItems() {
  return CartPage.items.filter(item => CartPage.selected.has(itemKey(item)));
}

function renderSummary() {
  const summary = document.getElementById('cartSummary');
  const selected = selectedItems();
  const count = selected.reduce((sum, item) => sum + Math.max(1, Number(item.quantity || 1)), 0);
  const total = selected.reduce((sum, item) => sum + Number(item.finalPrice || item.price || 0) * Math.max(1, Number(item.quantity || 1)), 0);
  const original = selected.reduce((sum, item) => sum + Number(item.originalPrice || item.finalPrice || item.price || 0) * Math.max(1, Number(item.quantity || 1)), 0);
  const discount = Math.max(0, original - total);
  summary.innerHTML = `
    <h3>结算信息</h3>
    <div class="cart-summary-line"><span>已选商品</span><strong>${count} 件</strong></div>
    <div class="cart-summary-line"><span>商品总价</span><span>${cartMoney(original)}</span></div>
    <div class="cart-summary-line"><span>优惠立减</span><span class="save-badge">-${cartMoney(discount)}</span></div>
    <div class="cart-summary-line cart-total"><span>应付合计</span><strong>${cartMoney(total)}</strong></div>
    <button class="cart-checkout-btn" id="checkoutBtn" ${selected.length ? '' : 'disabled'}>去结算</button>
  `;
  const checkout = document.getElementById('checkoutBtn');
  if (checkout) {
    checkout.addEventListener('click', () => {
      if (!selected.length) return;
      window.NovaOrder.open({ items: selected, source: 'cart', onSuccess: removeSelectedAfterOrder });
    });
  }
}

function bindCartEvents() {
  const selectAll = document.getElementById('selectAllCart');
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      CartPage.selected = selectAll.checked ? new Set(CartPage.items.map(itemKey)) : new Set();
      renderCart();
    });
  }

  const clearBtn = document.getElementById('clearCartBtn');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (!confirm('确定清空购物车吗？')) return;
      CartPage.items = [];
      CartPage.selected = new Set();
      saveCartItems();
      renderCart();
    });
  }

  document.querySelectorAll('.cart-select-input').forEach(input => {
    input.addEventListener('change', () => {
      const item = CartPage.items[Number(input.dataset.index)];
      const key = itemKey(item);
      if (input.checked) CartPage.selected.add(key); else CartPage.selected.delete(key);
      renderSummary();
    });
  });

  document.querySelectorAll('.qty-minus,.qty-plus').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = Number(btn.dataset.index);
      const current = Math.max(1, Number(CartPage.items[index].quantity || 1));
      CartPage.items[index].quantity = Math.max(1, Math.min(99, current + (btn.classList.contains('qty-plus') ? 1 : -1)));
      saveCartItems();
      renderCart();
    });
  });

  document.querySelectorAll('.qty-input').forEach(input => {
    input.addEventListener('change', () => {
      const index = Number(input.dataset.index);
      CartPage.items[index].quantity = Math.max(1, Math.min(99, Number(input.value) || 1));
      saveCartItems();
      renderCart();
    });
  });

  document.querySelectorAll('.cart-remove-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = Number(btn.dataset.index);
      const item = CartPage.items[index];
      CartPage.selected.delete(itemKey(item));
      CartPage.items.splice(index, 1);
      saveCartItems();
      renderCart();
    });
  });
}

function removeSelectedAfterOrder() {
  const keys = new Set(selectedItems().map(itemKey));
  CartPage.items = CartPage.items.filter(item => !keys.has(itemKey(item)));
  CartPage.selected = new Set();
  saveCartItems();
  renderCart();
}

document.addEventListener('DOMContentLoaded', () => {
  loadCartItems();
  renderCart();
});
