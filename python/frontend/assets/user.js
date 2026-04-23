const form = document.getElementById("recommend-form");
const submitBtn = document.getElementById("submitBtn");
const requestState = document.getElementById("requestState");
const productGrid = document.getElementById("productGrid");
const copyList = document.getElementById("copyList");
const metaLine = document.getElementById("metaLine");

function setState(message, stateClass) {
  requestState.textContent = message;
  requestState.className = "status";
  if (stateClass) {
    requestState.classList.add(stateClass);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderCopies(copies) {
  if (!copies || copies.length === 0) {
    copyList.innerHTML = "";
    return;
  }

  const html = copies
    .map((item, idx) => {
      const title = item.title || "Copy " + (idx + 1);
      const body = item.copy || item.content || JSON.stringify(item);
      return "<article class=\"copy-item\"><strong>" + escapeHtml(title) + "</strong><div>" + escapeHtml(body) + "</div></article>";
    })
    .join("");

  copyList.innerHTML = html;
}

function renderProducts(products) {
  if (!products || products.length === 0) {
    productGrid.innerHTML = "<div class=\"status\">No products returned.</div>";
    return;
  }

  const html = products
    .map((p) => {
      return [
        "<article class=\"product-card\">",
        "  <div class=\"product-name\">" + escapeHtml(p.name || p.product_id) + "</div>",
        "  <div class=\"product-meta\">Category: " + escapeHtml(p.category || "-") + "</div>",
        "  <div class=\"product-meta\">Brand: " + escapeHtml(p.brand || "-") + " | Stock: " + escapeHtml(p.stock ?? "-") + "</div>",
        "  <div class=\"product-price\">$" + escapeHtml(p.price ?? "-") + "</div>",
        "</article>",
      ].join("");
    })
    .join("");

  productGrid.innerHTML = html;
}

function buildPayload() {
  const userId = document.getElementById("userId").value.trim();
  const scene = document.getElementById("scene").value.trim() || "homepage";
  const numItems = Number(document.getElementById("numItems").value || 5);
  const recentViewsRaw = document.getElementById("recentViews").value.trim();

  const recentViews = recentViewsRaw
    ? recentViewsRaw.split(",").map((x) => x.trim()).filter(Boolean)
    : [];

  return {
    user_id: userId,
    scene,
    num_items: numItems,
    context: {
      recent_views: recentViews,
    },
  };
}

async function submitRecommend(event) {
  event.preventDefault();
  const payload = buildPayload();

  submitBtn.disabled = true;
  setState("Running recommendation pipeline...", "loading");

  try {
    const response = await fetch("/api/v1/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error("Request failed: " + response.status + " " + text);
    }

    const data = await response.json();
    renderProducts(data.products || []);
    renderCopies(data.marketing_copies || []);

    const latency = typeof data.total_latency_ms === "number" ? data.total_latency_ms.toFixed(1) : "-";
    metaLine.textContent = "Group: " + (data.experiment_group || "-") + " | Latency(ms): " + latency;

    setState("Recommendation completed.", "ok");
  } catch (error) {
    setState("Failed: " + error.message, "error");
    productGrid.innerHTML = "";
    copyList.innerHTML = "";
    metaLine.textContent = "Request failed";
  } finally {
    submitBtn.disabled = false;
  }
}

form.addEventListener("submit", submitRecommend);
