const form = document.getElementById("recommend-form");
const submitBtn = document.getElementById("submitBtn");
const requestState = document.getElementById("requestState");
const productGrid = document.getElementById("productGrid");
const copyList = document.getElementById("copyList");
const reasonList = document.getElementById("reasonList");
const metaLine = document.getElementById("metaLine");

const userIdInput = document.getElementById("userId");
const sceneInput = document.getElementById("scene");
const numItemsInput = document.getElementById("numItems");
const recentViewsInput = document.getElementById("recentViews");

const userIdHint = document.getElementById("userIdHint");
const numItemsHint = document.getElementById("numItemsHint");
const recentViewsHint = document.getElementById("recentViewsHint");

const MIN_ITEMS = 1;
const MAX_ITEMS = 20;
const MAX_RECENT_VIEWS = 20;

const UI_STATE = {
  IDLE: "idle",
  LOADING: "loading",
  SUCCESS: "success",
  ERROR: "error",
};

function setHint(element, message, isError) {
  if (!element) {
    return;
  }
  element.textContent = message;
  element.className = "field-hint";
  if (isError) {
    element.classList.add("error");
  }
}

function setInputValidity(input, isValid) {
  if (!input) {
    return;
  }
  input.classList.toggle("input-invalid", !isValid);
}

function setRequestState(state, message) {
  if (state === UI_STATE.LOADING) {
    AppUI.setButtonBusy(submitBtn, true, "Running...", "Run Recommendation");
    AppUI.setStatus(requestState, message, "loading");
    return;
  }

  AppUI.setButtonBusy(submitBtn, false, "Running...", "Run Recommendation");

  if (state === UI_STATE.SUCCESS) {
    AppUI.setStatus(requestState, message, "ok");
    return;
  }
  if (state === UI_STATE.ERROR) {
    AppUI.setStatus(requestState, message, "error");
    return;
  }
  AppUI.setStatus(requestState, message, "subtle");
}

function parseRecentViews(rawText) {
  const parsed = AppUI.normalizeCsv(rawText);
  const uniqueValues = [];
  const seen = new Set();

  for (const item of parsed) {
    const normalized = item.toLowerCase();
    if (!seen.has(normalized)) {
      seen.add(normalized);
      uniqueValues.push(item);
    }
  }

  let values = uniqueValues;
  let hint = "Example: phone, earphones, laptop";

  if (parsed.length !== uniqueValues.length) {
    hint = "Duplicate items were removed automatically.";
  }

  if (uniqueValues.length > MAX_RECENT_VIEWS) {
    values = uniqueValues.slice(0, MAX_RECENT_VIEWS);
    hint = "Only the first " + MAX_RECENT_VIEWS + " items are used.";
  }

  return {
    values: values,
    hint: hint,
  };
}

function buildPayloadWithValidation() {
  let isValid = true;

  const userId = userIdInput.value.trim();
  if (!userId) {
    isValid = false;
    setInputValidity(userIdInput, false);
    setHint(userIdHint, "User ID cannot be empty.", true);
  } else {
    setInputValidity(userIdInput, true);
    setHint(userIdHint, "Required. Example: user_001", false);
  }

  const parsedNumItems = AppUI.toInt(numItemsInput.value, NaN);
  if (!Number.isInteger(parsedNumItems) || parsedNumItems < MIN_ITEMS || parsedNumItems > MAX_ITEMS) {
    isValid = false;
    setInputValidity(numItemsInput, false);
    setHint(numItemsHint, "Number of items must be between " + MIN_ITEMS + " and " + MAX_ITEMS + ".", true);
  } else {
    setInputValidity(numItemsInput, true);
    setHint(numItemsHint, "Allowed range: " + MIN_ITEMS + "-" + MAX_ITEMS + ".", false);
  }

  const recentViewsParsed = parseRecentViews(recentViewsInput.value);
  setHint(recentViewsHint, recentViewsParsed.hint, false);

  if (!isValid) {
    return {
      isValid: false,
      payload: null,
    };
  }

  const normalizedNumItems = AppUI.clampInt(parsedNumItems, MIN_ITEMS, MAX_ITEMS);
  numItemsInput.value = String(normalizedNumItems);

  return {
    isValid: true,
    payload: {
      user_id: userId,
      scene: sceneInput.value.trim() || "homepage",
      num_items: normalizedNumItems,
      context: {
        recent_views: recentViewsParsed.values,
      },
    },
  };
}

function renderCopies(copies) {
  if (!copies || copies.length === 0) {
    copyList.innerHTML = "<div class=\"empty-state\">No marketing copy returned for this request.</div>";
    return;
  }

  const html = copies
    .map((item, idx) => {
      const title = item.title || "Copy " + (idx + 1);
      const body = item.copy || item.content || JSON.stringify(item);
      return "<article class=\"copy-item\"><strong>" + AppUI.escapeHtml(title) + "</strong><div>" + AppUI.escapeHtml(body) + "</div></article>";
    })
    .join("");

  copyList.innerHTML = html;
}

function collectReasons(data, products) {
  const collected = [];

  if (typeof data.explain === "string" && data.explain.trim()) {
    collected.push(data.explain.trim());
  }
  if (Array.isArray(data.explain)) {
    for (const item of data.explain) {
      if (typeof item === "string" && item.trim()) {
        collected.push(item.trim());
      }
    }
  }
  if (data.explain && typeof data.explain === "object" && !Array.isArray(data.explain)) {
    for (const key of Object.keys(data.explain)) {
      const value = data.explain[key];
      if (value !== null && value !== undefined) {
        collected.push(key + ": " + String(value));
      }
    }
  }

  for (const product of products) {
    const reasonValue = product.explain || product.reason || product.match_reason || product.why;
    if (typeof reasonValue === "string" && reasonValue.trim()) {
      collected.push((product.name || product.product_id || "Item") + ": " + reasonValue.trim());
    }
  }

  const deduped = [];
  const seen = new Set();
  for (const reason of collected) {
    const normalized = reason.toLowerCase();
    if (!seen.has(normalized)) {
      deduped.push(reason);
      seen.add(normalized);
    }
  }

  return deduped.slice(0, 8);
}

function renderReasons(data, products) {
  const reasons = collectReasons(data, products);
  if (reasons.length === 0) {
    reasonList.innerHTML = "<div class=\"empty-state\">No explain field available yet. This area will show recommendation reasons when backend explain data is provided.</div>";
    return;
  }

  reasonList.innerHTML = reasons
    .map((reason) => {
      return "<div class=\"reason-item\">" + AppUI.escapeHtml(reason) + "</div>";
    })
    .join("");
}

function renderProducts(products) {
  if (!products || products.length === 0) {
    productGrid.innerHTML = "<div class=\"empty-state\">No products returned. Try changing scene or recent views and submit again.</div>";
    return;
  }

  const html = products
    .map((product) => {
      return [
        "<article class=\"product-card\">",
        "  <div class=\"product-name\">" + AppUI.escapeHtml(product.name || product.product_id || "Unnamed product") + "</div>",
        "  <div class=\"product-meta\">Category: " + AppUI.escapeHtml(product.category || "-") + "</div>",
        "  <div class=\"product-meta\">Brand: " + AppUI.escapeHtml(product.brand || "-") + " | Stock: " + AppUI.escapeHtml(product.stock ?? "-") + "</div>",
        "  <div class=\"product-price\">$" + AppUI.escapeHtml(product.price ?? "-") + "</div>",
        "</article>",
      ].join("");
    })
    .join("");

  productGrid.innerHTML = html;
}

function renderMetaLine(data) {
  const group = data.experiment_group || "-";
  const latency = AppUI.formatLatency(data.total_latency_ms);
  const count = Array.isArray(data.products) ? data.products.length : 0;
  metaLine.textContent = "Group: " + group + " | Latency(ms): " + latency + " | Products: " + count;
}

function showInitialPlaceholders() {
  copyList.innerHTML = "<div class=\"empty-state\">Run a recommendation to see generated marketing copy.</div>";
  reasonList.innerHTML = "<div class=\"empty-state\">Reason details will appear here.</div>";
  productGrid.innerHTML = "<div class=\"empty-state\">No request yet.</div>";
}

async function submitRecommend(event) {
  event.preventDefault();

  const built = buildPayloadWithValidation();
  if (!built.isValid) {
    setRequestState(UI_STATE.ERROR, "Please fix highlighted fields and try again.");
    return;
  }

  setRequestState(UI_STATE.LOADING, "Running recommendation pipeline...");

  try {
    const data = await AppUI.fetchJson("/api/v1/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(built.payload),
    });

    const products = AppUI.asArray(data.products);
    renderProducts(products);
    renderCopies(AppUI.asArray(data.marketing_copies));
    renderReasons(data, products);
    renderMetaLine(data);

    const successMessage = products.length > 0
      ? "Recommendation completed successfully."
      : "Request completed. No products matched this context.";
    setRequestState(UI_STATE.SUCCESS, successMessage);
  } catch (error) {
    showInitialPlaceholders();
    metaLine.textContent = "Request failed";
    setRequestState(UI_STATE.ERROR, "Request failed: " + (error.message || "Unknown error"));
  }
}

userIdInput.addEventListener("input", () => {
  if (userIdInput.value.trim()) {
    setInputValidity(userIdInput, true);
    setHint(userIdHint, "Required. Example: user_001", false);
  }
});

numItemsInput.addEventListener("input", () => {
  const parsedNumItems = AppUI.toInt(numItemsInput.value, NaN);
  const validRange = Number.isInteger(parsedNumItems) && parsedNumItems >= MIN_ITEMS && parsedNumItems <= MAX_ITEMS;
  setInputValidity(numItemsInput, validRange);
  if (!validRange) {
    setHint(numItemsHint, "Number of items must be between " + MIN_ITEMS + " and " + MAX_ITEMS + ".", true);
    return;
  }
  setHint(numItemsHint, "Allowed range: " + MIN_ITEMS + "-" + MAX_ITEMS + ".", false);
});

recentViewsInput.addEventListener("input", () => {
  const parsed = parseRecentViews(recentViewsInput.value);
  setHint(recentViewsHint, parsed.hint, false);
});

form.addEventListener("submit", submitRecommend);

setRequestState(UI_STATE.IDLE, "Ready.");
showInitialPlaceholders();
