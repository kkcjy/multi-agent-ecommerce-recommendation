(function initNovaOrder(global) {
  const ADDRESSES = [
    { id: 'addr_home', name: '张伟', phone: '138****6688', text: '北京市朝阳区望京 SOHO T2 18 层', tag: '默认地址' },
    { id: 'addr_company', name: '王芳', phone: '136****2890', text: '深圳市南山区科技园软件产业基地 5 栋', tag: '公司地址' },
  ];

  const PAYMENTS = [
    { id: 'alipay', label: '支付宝', icon: '💙' },
    { id: 'wechat', label: '微信支付', icon: '💚' },
    { id: 'card', label: '银行卡', icon: '💳' },
  ];

  const state = {
    items: [],
    source: 'buy_now',
    addressId: ADDRESSES[0].id,
    paymentId: PAYMENTS[0].id,
    onSuccess: null,
  };

  function esc(value) { return AppUI.escapeHtml(value ?? ''); }
  function money(value) { return '¥' + Number(value || 0).toLocaleString('zh-CN'); }
  function currentUserId() { return AppUI.getCurrentUserId(); }
  function ordersKey() { return 'orders_' + currentUserId(); }
  function getOrders() {
    try { return JSON.parse(localStorage.getItem(ordersKey()) || '[]'); } catch { return []; }
  }
  function saveOrders(orders) { localStorage.setItem(ordersKey(), JSON.stringify(orders)); }
  function normalizeOrderItem(item) {
    const p = AppUI.normalizeProduct(item);
    return {
      product_id: p.product_id,
      name: p.name,
      category: p.category,
      brand: p.brand,
      image_url: p.image_url,
      price: p.finalPrice || p.price,
      finalPrice: p.finalPrice || p.price,
      originalPrice: p.originalPrice,
      quantity: Math.max(1, Number(item.quantity || item.qty || 1)),
      sku: item.sku || {},
    };
  }

  function ensureModal() {
    if (document.getElementById('orderModal')) return;
    document.body.insertAdjacentHTML('beforeend', `
      <div class="order-modal" id="orderModal" aria-hidden="true">
        <div class="order-dialog" role="dialog" aria-modal="true" aria-labelledby="orderTitle">
          <div class="order-dialog-head">
            <div>
              <h3 id="orderTitle">确认订单</h3>
              <p class="muted">选择收货地址与支付方式，模拟真实下单流程</p>
            </div>
            <button class="order-close-btn" type="button" id="orderCloseBtn">×</button>
          </div>
          <div id="orderBody"></div>
        </div>
      </div>
      <div class="order-success-modal" id="orderSuccessModal" aria-hidden="true">
        <div class="order-success-dialog" role="dialog" aria-modal="true">
          <div id="orderSuccessBody"></div>
        </div>
      </div>
    `);
    document.getElementById('orderCloseBtn').addEventListener('click', close);
    document.getElementById('orderModal').addEventListener('click', event => {
      if (event.target.id === 'orderModal') close();
    });
    document.getElementById('orderSuccessModal').addEventListener('click', event => {
      if (event.target.id === 'orderSuccessModal') closeSuccess();
    });
  }

  function render() {
    const body = document.getElementById('orderBody');
    const total = state.items.reduce((sum, item) => sum + Number(item.finalPrice || item.price || 0) * Math.max(1, Number(item.quantity || 1)), 0);
    const original = state.items.reduce((sum, item) => sum + Number(item.originalPrice || item.finalPrice || item.price || 0) * Math.max(1, Number(item.quantity || 1)), 0);
    body.innerHTML = `
      <section class="order-section">
        <div class="order-section-head"><strong>收货地址</strong><span class="muted">预置演示地址</span></div>
        <div class="address-list">
          ${ADDRESSES.map(addr => `
            <label class="address-option">
              <input type="radio" name="orderAddress" value="${addr.id}" ${addr.id === state.addressId ? 'checked' : ''} />
              <span><strong>${esc(addr.name)} ${esc(addr.phone)}</strong><br><span>${esc(addr.text)}</span><br><small class="save-badge">${esc(addr.tag)}</small></span>
            </label>
          `).join('')}
        </div>
      </section>
      <section class="order-section">
        <div class="order-section-head"><strong>支付方式</strong><span class="muted">演示支付不扣款</span></div>
        <div class="payment-list">
          ${PAYMENTS.map(pay => `
            <label class="payment-option">
              <input type="radio" name="orderPayment" value="${pay.id}" ${pay.id === state.paymentId ? 'checked' : ''} />
              <span>${pay.icon} ${esc(pay.label)}</span>
            </label>
          `).join('')}
        </div>
      </section>
      <section class="order-section">
        <div class="order-section-head"><strong>商品确认</strong><span class="muted">${state.items.length} 个商品</span></div>
        <div class="order-products">
          ${state.items.map(item => `
            <div class="order-product-row">
              <img src="${esc(item.image_url || '')}" alt="${esc(item.name)}" onerror="this.style.display='none'" />
              <div>
                <strong>${esc(item.name)}</strong>
                <div class="muted">${esc(Object.values(item.sku || {}).filter(Boolean).join(' / ') || item.brand || item.category || '官方标配')}</div>
              </div>
              <div style="text-align:right"><strong>${money(item.finalPrice || item.price)}</strong><br><span class="muted">× ${item.quantity}</span></div>
            </div>
          `).join('')}
        </div>
        <div class="order-total-line"><span>商品原价</span><span>${money(original)}</span></div>
        <div class="order-total-line"><span>优惠立减</span><span class="save-badge">-${money(Math.max(0, original - total))}</span></div>
        <div class="order-total-line"><span>应付金额</span><strong style="color:var(--accent-2);font-size:1.25rem">${money(total)}</strong></div>
      </section>
      <button class="order-submit-btn" id="submitOrderBtn" type="button">提交订单</button>
    `;

    body.querySelectorAll('input[name="orderAddress"]').forEach(input => {
      input.addEventListener('change', () => { state.addressId = input.value; });
    });
    body.querySelectorAll('input[name="orderPayment"]').forEach(input => {
      input.addEventListener('change', () => { state.paymentId = input.value; });
    });
    document.getElementById('submitOrderBtn').addEventListener('click', submitOrder);
  }

  function open(options) {
    ensureModal();
    const rawItems = options && options.items ? options.items : [options && options.product].filter(Boolean);
    state.items = rawItems.map(normalizeOrderItem).filter(item => item.product_id);
    if (!state.items.length) {
      AppUI.toast('没有可下单的商品', 'error');
      return;
    }
    state.source = (options && options.source) || 'buy_now';
    state.onSuccess = options && options.onSuccess;
    render();
    const modal = document.getElementById('orderModal');
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }

  function close() {
    const modal = document.getElementById('orderModal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }

  function closeSuccess() {
    const modal = document.getElementById('orderSuccessModal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }

  function submitOrder() {
    const total = state.items.reduce((sum, item) => sum + Number(item.finalPrice || item.price || 0) * Math.max(1, Number(item.quantity || 1)), 0);
    const address = ADDRESSES.find(item => item.id === state.addressId) || ADDRESSES[0];
    const payment = PAYMENTS.find(item => item.id === state.paymentId) || PAYMENTS[0];
    const order = {
      order_id: 'NC' + Date.now() + Math.floor(Math.random() * 900 + 100),
      user_id: currentUserId(),
      items: state.items,
      address,
      payment,
      total_amount: Number(total.toFixed(2)),
      status: state.source === 'cart' ? '待发货' : '配送中',
      created_at: new Date().toLocaleString(),
      eta: new Date(Date.now() + 3 * 24 * 3600 * 1000).toLocaleDateString(),
    };
    const orders = getOrders();
    orders.unshift(order);
    saveOrders(orders.slice(0, 50));
    close();
    if (typeof state.onSuccess === 'function') state.onSuccess(order);
    showSuccess(order);
    AppUI.toast('下单成功', 'success');
  }

  function showSuccess(order) {
    ensureModal();
    const body = document.getElementById('orderSuccessBody');
    body.innerHTML = `
      <div style="text-align:center;padding:1rem">
        <div style="font-size:3.5rem">✅</div>
        <h3>下单成功</h3>
        <p class="muted">订单已写入当前用户历史订单，可在个人中心查看。</p>
      </div>
      <div class="order-section">
        <div class="order-total-line"><span>订单号</span><strong>${esc(order.order_id)}</strong></div>
        <div class="order-total-line"><span>订单金额</span><strong>${money(order.total_amount)}</strong></div>
        <div class="order-total-line"><span>订单状态</span><span class="save-badge">${esc(order.status)}</span></div>
        <div class="order-total-line"><span>预计送达</span><strong>${esc(order.eta)}</strong></div>
      </div>
      <div class="dialog-actions" style="margin-top:1rem">
        <button class="secondary-btn" type="button" id="successCloseBtn">继续购物</button>
        <a class="primary-btn" href="/user">查看订单</a>
      </div>
    `;
    document.getElementById('successCloseBtn').addEventListener('click', closeSuccess);
    const modal = document.getElementById('orderSuccessModal');
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }

  global.NovaOrder = {
    open,
    getOrders,
    saveOrders,
  };
})(window);
