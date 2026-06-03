(function initAppUI(global) {
  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function setStatus(element, message, tone) {
    if (!element) {
      return;
    }
    element.textContent = message;
    element.className = "status";
    if (tone) {
      element.classList.add(tone);
    }
  }

  function setButtonBusy(button, isBusy, busyText, idleText) {
    if (!button) {
      return;
    }
    if (isBusy) {
      if (!button.dataset.idleText) {
        button.dataset.idleText = idleText || button.textContent;
      }
      button.textContent = busyText || "Loading...";
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      return;
    }
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.textContent = button.dataset.idleText || idleText || button.textContent;
  }

  function flattenFastApiDetail(detail) {
    if (Array.isArray(detail)) {
      return detail
        .map(function mapDetail(item) {
          if (!item || typeof item !== "object") {
            return String(item || "");
          }
          var where = Array.isArray(item.loc) ? item.loc.join(".") + ": " : "";
          return where + (item.msg || JSON.stringify(item));
        })
        .filter(Boolean)
        .join("; ");
    }
    if (detail && typeof detail === "object") {
      return JSON.stringify(detail);
    }
    return String(detail || "");
  }

  async function parseFetchError(response) {
    var payloadText = "";
    try {
      payloadText = await response.text();
    } catch (error) {
      payloadText = "";
    }

    if (!payloadText) {
      return "HTTP " + response.status + " " + response.statusText;
    }

    try {
      var parsed = JSON.parse(payloadText);
      if (parsed && parsed.detail) {
        return flattenFastApiDetail(parsed.detail);
      }
      if (parsed && parsed.message) {
        return String(parsed.message);
      }
      return JSON.stringify(parsed);
    } catch (error) {
      return payloadText;
    }
  }

  async function fetchJson(url, options) {
    var response = await fetch(url, options || {});
    if (!response.ok) {
      var errorMessage = await parseFetchError(response);
      throw new Error(errorMessage || "Request failed");
    }
    return response.json();
  }

  function normalizeCsv(value) {
    return String(value || "")
      .replaceAll("，", ",")
      .split(",")
      .map(function trimToken(token) {
        return token.trim();
      })
      .filter(Boolean);
  }

  function toInt(value, fallback) {
    var n = Number.parseInt(String(value), 10);
    if (Number.isNaN(n)) {
      return fallback;
    }
    return n;
  }

  function clampInt(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function formatLatency(latencyMs) {
    if (typeof latencyMs !== "number" || Number.isNaN(latencyMs)) {
      return "-";
    }
    return latencyMs.toFixed(1);
  }

  function asArray(value) {
    if (Array.isArray(value)) {
      return value;
    }
    if (value === null || value === undefined) {
      return [];
    }
    return [value];
  }

  function unwrapApiPayload(payload) {
    if (payload && typeof payload === "object" && "code" in payload) {
      if (payload.code !== 0) {
        throw new Error(payload.message || "Request failed");
      }
      return payload.data;
    }
    return payload;
  }

  async function fetchApiJson(url, options) {
    var payload = await fetchJson(url, options || {});
    return unwrapApiPayload(payload);
  }

  function normalizeNumber(value, fallback) {
    var n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function deriveInventoryStatus(stock) {
    if (stock <= 0) {
      return "out_of_stock";
    }
    if (stock <= 60) {
      return "low_stock";
    }
    return "in_stock";
  }

  function normalizeProduct(raw) {
    var source = raw || {};
    var price = normalizeNumber(source.price, 0);
    var discount = normalizeNumber(source.discount, 0);
    var finalPrice = source.final_price !== undefined && source.final_price !== null
      ? normalizeNumber(source.final_price, price)
      : Math.max(0, price - discount);
    var originalPrice = source.original_price !== undefined && source.original_price !== null
      ? normalizeNumber(source.original_price, price)
      : price;
    if (!discount && originalPrice > finalPrice) {
      discount = originalPrice - finalPrice;
    }

    var tags = asArray(source.tags);
    var badges = asArray(source.badges);
    var priceTags = asArray(source.price_tags);
    var stock = normalizeNumber(source.stock, 0);
    var inventoryStatus = source.inventory_status || deriveInventoryStatus(stock);

    return {
      product_id: String(source.product_id || source.id || ""),
      name: String(source.name || ""),
      category: String(source.category || ""),
      brand: String(source.brand || ""),
      seller_id: String(source.seller_id || ""),
      price: finalPrice,
      finalPrice: finalPrice,
      originalPrice: originalPrice > finalPrice ? originalPrice : null,
      discount: discount,
      currency: source.currency || "CNY",
      stock: stock,
      inventory_status: inventoryStatus,
      sales: normalizeNumber(source.sales, 0),
      rating: normalizeNumber(source.rating || source.score, 0),
      review_count: normalizeNumber(source.review_count, 0),
      tags: tags,
      price_tags: priceTags,
      badges: badges,
      image_url: String(source.image_url || ""),
      image_urls: asArray(source.image_urls),
      external_url: String(source.external_url || ""),
      specs: source.specs || {},
      explain: source.explain || {},
    };
  }

  function getCurrentUserId() {
    var userId = localStorage.getItem("userId");
    if (!userId) {
      userId = "demo_tech";
      localStorage.setItem("userId", userId);
    }
    return userId;
  }

  function getAuth() {
    return safeJsonParse(localStorage.getItem("novacartAuth"), null);
  }

  function isLoggedIn() {
    return !!getAuth();
  }

  function isAdminLoggedIn() {
    var auth = getAuth();
    return !!auth && auth.role === "admin" && !!localStorage.getItem("novacartAdminApiKey");
  }

  function logoutAuth() {
    localStorage.removeItem("novacartAuth");
    localStorage.removeItem("novacartAdminApiKey");
    localStorage.removeItem("novacartAdminName");
    localStorage.removeItem("userId");
  }

  function enforcePageAuth() {
    var path = global.location.pathname;
    if (path === "/login" || path === "/docs" || path === "/redoc") {
      return;
    }
    if (path === "/admin") {
      if (!isAdminLoggedIn()) {
        global.location.href = "/login?role=admin";
      }
      return;
    }
    var protectedPaths = ["/home", "/user", "/category", "/search", "/cart"];
    var isProductPage = path.indexOf("/product/") === 0;
    if ((protectedPaths.indexOf(path) >= 0 || isProductPage) && !isLoggedIn()) {
      global.location.href = "/login";
    }
  }

  function storageKey(prefix, userId) {
    return prefix + "_" + (userId || getCurrentUserId());
  }

  function safeJsonParse(value, fallback) {
    try {
      return JSON.parse(value || "");
    } catch (error) {
      return fallback;
    }
  }

  function getCart(userId) {
    return safeJsonParse(localStorage.getItem(storageKey("cart", userId)), []);
  }

  function saveCart(items, userId) {
    localStorage.setItem(storageKey("cart", userId), JSON.stringify(asArray(items)));
    updateCartBadge();
    try {
      global.dispatchEvent(new CustomEvent("novacart:cart-updated", { detail: { userId: userId || getCurrentUserId() } }));
    } catch (error) {
      // CustomEvent is not available in very old browsers; badge already updated.
    }
  }

  function cartCount(userId) {
    return getCart(userId).reduce(function sum(total, item) {
      return total + Math.max(1, normalizeNumber(item.quantity, 1));
    }, 0);
  }

  function addToCart(product, quantity, sku, userId) {
    var normalized = normalizeProduct(product);
    if (!normalized.product_id) {
      return { ok: false, message: "商品信息不完整" };
    }
    var qty = Math.max(1, Math.floor(normalizeNumber(quantity, 1)));
    var currentUser = userId || getCurrentUserId();
    var items = getCart(currentUser);
    var skuKey = JSON.stringify(sku || {});
    var existing = items.find(function findItem(item) {
      return item.product_id === normalized.product_id && JSON.stringify(item.sku || {}) === skuKey;
    });
    if (existing) {
      existing.quantity = Math.min(99, Math.max(1, normalizeNumber(existing.quantity, 1) + qty));
      existing.updated_at = new Date().toISOString();
    } else {
      items.unshift({
        product_id: normalized.product_id,
        name: normalized.name,
        category: normalized.category,
        brand: normalized.brand,
        price: normalized.price,
        finalPrice: normalized.finalPrice,
        originalPrice: normalized.originalPrice,
        discount: normalized.discount,
        image_url: normalized.image_url,
        stock: normalized.stock,
        rating: normalized.rating,
        sales: normalized.sales,
        quantity: qty,
        sku: sku || {},
        added_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
    saveCart(items, currentUser);
    return { ok: true, count: cartCount(currentUser), items: items };
  }

  function updateCartBadge() {
    var count = cartCount();
    document.querySelectorAll("[data-cart-count]").forEach(function updateBadge(el) {
      el.textContent = String(count);
      el.style.display = count > 0 ? "inline-flex" : "none";
    });
  }

  function ratingStars(rating) {
    var score = Math.max(0, Math.min(5, normalizeNumber(rating, 0)));
    var full = Math.round(score);
    return "★★★★★".slice(0, full) + "☆☆☆☆☆".slice(0, 5 - full);
  }

  function productCardActionsHtml(productId) {
    return '<button class="card-cart-btn" type="button" data-cart-add="' + escapeHtml(productId || "") + '">加入购物车</button>';
  }

  function toast(message, type) {
    var container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    var el = document.createElement("div");
    el.className = "toast " + (type || "");
    el.textContent = message;
    container.appendChild(el);
    setTimeout(function removeToast() {
      el.style.opacity = "0";
      el.style.transform = "translateY(8px)";
      setTimeout(function detach() { el.remove(); }, 220);
    }, 2200);
  }

  function enhanceHeader() {
    if (document.body && document.body.classList.contains("page-admin")) {
      return;
    }
    var header = document.querySelector(".site-header .header-inner") || document.querySelector(".topbar");
    if (!header || header.querySelector(".commerce-actions")) {
      updateCartBadge();
      return;
    }
    var actions = document.createElement("div");
    actions.className = "commerce-actions";
    actions.innerHTML = '<button class="notify-btn" type="button" aria-label="消息通知"><span>🔔</span><span class="notify-dot"></span></button><a class="cart-link" href="/cart" aria-label="购物车"><span class="cart-icon">🛒</span><span>购物车</span><span class="cart-badge" data-cart-count>0</span></a>';
    header.appendChild(actions);
    updateCartBadge();
  }

  function bindCartButtons(products, root) {
    var scope = root || document;
    var list = normalizeProducts(products);
    scope.querySelectorAll("[data-cart-add]").forEach(function bind(btn) {
      if (btn.dataset.cartBound === "1") {
        return;
      }
      btn.dataset.cartBound = "1";
      btn.addEventListener("click", function onAdd(event) {
        event.preventDefault();
        event.stopPropagation();
        var id = btn.dataset.cartAdd;
        var product = list.find(function match(item) { return item.product_id === id; });
        if (!product) {
          toast("商品信息缺失，暂时无法加入购物车", "error");
          return;
        }
        addToCart(product, 1, {});
        toast("已加入购物车", "success");
      });
    });
  }

  function defaultFooterHtml() {
    return '<footer class="site-footer"><div class="footer-inner"><div class="footer-section"><h4>关于我们</h4><a href="#">公司简介</a><a href="#">营业执照</a></div><div class="footer-section"><h4>帮助中心</h4><a href="#">购物指南</a><a href="#">退换货政策</a></div><div class="footer-section"><h4>联系客服</h4><a href="#">在线客服</a><a href="#">售后服务</a></div><div class="footer-section"><h4>隐私政策</h4><a href="#">用户协议</a><a href="#">隐私保护</a></div></div><div class="footer-bottom"><p>&copy; 2026 NovaCart · 多 Agent 智能电商推荐系统</p></div></footer>';
  }

  function ensureFooter() {
    if (!document.querySelector(".site-footer") && document.body) {
      document.body.insertAdjacentHTML("beforeend", defaultFooterHtml());
    }
  }

  document.addEventListener("DOMContentLoaded", function initCommonCommerce() {
    enforcePageAuth();
    enhanceHeader();
    ensureFooter();
    updateCartBadge();
  });

  global.addEventListener("storage", function onStorage(event) {
    if (event.key && event.key.indexOf("cart_") === 0) {
      updateCartBadge();
    }
  });

  function normalizeProducts(items) {
    return asArray(items).map(normalizeProduct);
  }

  global.AppUI = {
    asArray: asArray,
    clampInt: clampInt,
    escapeHtml: escapeHtml,
    fetchApiJson: fetchApiJson,
    fetchJson: fetchJson,
    formatLatency: formatLatency,
    normalizeProduct: normalizeProduct,
    normalizeProducts: normalizeProducts,
    normalizeCsv: normalizeCsv,
    normalizeNumber: normalizeNumber,
    parseFetchError: parseFetchError,
    setButtonBusy: setButtonBusy,
    setStatus: setStatus,
    toInt: toInt,
    unwrapApiPayload: unwrapApiPayload,
    getAuth: getAuth,
    isLoggedIn: isLoggedIn,
    isAdminLoggedIn: isAdminLoggedIn,
    logoutAuth: logoutAuth,
    getCurrentUserId: getCurrentUserId,
    getCart: getCart,
    saveCart: saveCart,
    addToCart: addToCart,
    cartCount: cartCount,
    updateCartBadge: updateCartBadge,
    bindCartButtons: bindCartButtons,
    enhanceHeader: enhanceHeader,
    ensureFooter: ensureFooter,
    ratingStars: ratingStars,
    productCardActionsHtml: productCardActionsHtml,
    toast: toast,
  };
})(window);