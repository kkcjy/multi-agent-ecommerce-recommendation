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
      product_id: String(source.product_id || ""),
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
      rating: normalizeNumber(source.rating, 0),
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
  };
})(window);