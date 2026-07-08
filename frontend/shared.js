(() => {
  "use strict";

  const scriptUrl = new URL(document.currentScript.src);
  const pages = {
    home: new URL("index.html", scriptUrl),
    categories: new URL("categories.html", scriptUrl),
    product: new URL("product.html", scriptUrl),
    source: new URL("info.html?view=source", scriptUrl),
    disclaimer: new URL("info.html?view=disclaimer", scriptUrl),
    list: new URL("list.html", scriptUrl),
  };
  const assets = new URL("image/", scriptUrl);
  const developmentApiBase = ["5500", "5501"].includes(location.port) ? "http://127.0.0.1:8000" : location.origin;
  const apiBase = localStorage.getItem("foodTraceApiBase") || developmentApiBase;
  const clientId = getClientId();
  const declaredPage = document.body.dataset.page;
  const page = declaredPage === "info"
    ? (new URLSearchParams(location.search).get("view") === "disclaimer" ? "disclaimer" : "source")
    : declaredPage;

  function getClientId() {
    let value = localStorage.getItem("foodTraceClientId");
    if (!value) {
      value = globalThis.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      localStorage.setItem("foodTraceClientId", value);
    }
    return value;
  }

  function url(name, params = {}) {
    const target = new URL(pages[name]);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") target.searchParams.set(key, value);
    });
    return target.href;
  }

  function imageAsset(name) {
    return new URL(name, assets).href;
  }

  function getCategoryIcon(name) {
    const n = name || "";
    if (n.includes("蛋")) return "egg_alt";
    if (n.includes("乳") || n.includes("奶")) return "local_drink";
    if (n.includes("蔬") || n.includes("果")) return "nutrition";
    if (n.includes("肉") || n.includes("水產") || n.includes("魚") || n.includes("海鮮")) return "set_meal";
    if (n.includes("油")) return "opacity";
    if (n.includes("即食") || n.includes("便當") || n.includes("餐")) return "lunch_dining";
    if (n.includes("罐") || n.includes("加工")) return "inventory_2";
    if (n.includes("調味") || n.includes("醬") || n.includes("調料")) return "soup_kitchen";
    if (n.includes("添加")) return "science";
    if (n.includes("飲") || n.includes("冰") || n.includes("水") || n.includes("咖啡") || n.includes("茶")) return "local_drink";
    if (n.includes("零食") || n.includes("餅") || n.includes("點心") || n.includes("糖果")) return "cookie";
    if (n.includes("五穀") || n.includes("穀") || n.includes("麥") || n.includes("米") || n.includes("雜糧")) return "bakery_dining";
    return "restaurant";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.client !== false) headers.set("X-Client-ID", clientId);
    const response = await fetch(`${apiBase}${path}`, { ...options, headers });
    if (!response.ok) {
      let message = `連線失敗（${response.status}）`;
      try {
        const body = await response.json();
        if (body.detail) message = body.detail;
      } catch (_) {}
      throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
  }

  function loading(message = "正在讀取資料…") {
    return `<div class="py-16 text-center text-outline flex flex-col items-center justify-center" aria-busy="true" aria-live="polite">
      <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
      <p class="mt-4 font-medium text-text-muted">${escapeHtml(message)}</p>
    </div>`;
  }

  function emptyState(title, detail, actionHref = url("home"), actionLabel = "返回首頁") {
    const btnHtml = actionHref
      ? `<a href="${actionHref}" class="inline-flex mt-5 px-6 py-3 rounded-full bg-primary text-white font-label-lg hover:bg-on-primary-container transition-all duration-200 active:scale-95 shadow-sm min-h-[44px] items-center justify-center">${escapeHtml(actionLabel)}</a>`
      : "";
    return `<div class="col-span-full w-full min-h-[280px] bg-white/80 backdrop-blur-md border border-border-light rounded-2xl p-8 text-center shadow-[0_8px_30px_rgb(0,0,0,0.04)] mx-auto transition-all duration-300 flex flex-col items-center justify-center">
      <span class="material-symbols-outlined text-primary text-5xl">inventory_2</span>
      <h2 class="font-headline-md text-headline-md mt-3 text-on-surface">${escapeHtml(title)}</h2>
      <p class="text-text-muted mt-2 text-sm">${escapeHtml(detail)}</p>
      ${btnHtml}
    </div>`;
  }

  function searchPromptState(label) {
    return `<div class="min-h-[360px] flex flex-col items-center justify-center text-center px-6">
      <div class="relative w-36 h-24 flex items-center justify-center">
        <div class="absolute inset-x-2 top-5 bottom-1 rounded-[50%] bg-primary-container/70 -rotate-6"></div>
        <span class="material-symbols-outlined relative text-primary text-7xl">search</span>
      </div>
      <p class="mt-4 text-on-surface-variant font-medium">搜尋${escapeHtml(label)}以查看結果</p>
    </div>`;
  }

  function errorState(error, retry) {
    const id = `retry-${Math.random().toString(36).slice(2)}`;
    queueMicrotask(() => document.getElementById(id)?.addEventListener("click", retry));
    return `<div class="col-span-full w-full bg-error-container/40 backdrop-blur-md text-on-error-container rounded-2xl p-8 flex flex-col items-center justify-center text-center border border-error-container transition-all duration-300">
      <span class="material-symbols-outlined text-error text-4xl mb-3">cloud_off</span>
      <p class="font-headline-sm font-semibold">資料暫時無法載入</p>
      <p class="text-sm mt-2 opacity-90">${escapeHtml(error.message)}</p>
      <button id="${id}" class="mt-5 px-6 py-2.5 bg-white text-error font-label-lg rounded-full border border-error-container/50 hover:bg-surface transition-all active:scale-95 shadow-sm min-h-[44px]">重新嘗試</button>
    </div>`;
  }

  function toast(message) {
    document.getElementById("food-trace-toast")?.remove();
    const el = document.createElement("div");
    el.id = "food-trace-toast";
    el.className = "fixed left-1/2 bottom-24 -translate-x-1/2 z-[100] bg-on-surface/90 backdrop-blur-md text-white rounded-full px-6 py-3 shadow-lg text-sm transition-all duration-300 opacity-0 transform translate-y-2";
    el.textContent = message;
    document.body.append(el);
    requestAnimationFrame(() => {
      el.classList.remove("opacity-0", "translate-y-2");
    });
    setTimeout(() => {
      el.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => el.remove(), 300);
    }, 2200);
  }

  function productImage(product) {
    return product.image_available && product.front_image
      ? product.front_image
      : imageAsset("暫無產品圖片.png");
  }

  function attachImageFallback(root = document) {
    root.querySelectorAll("img[data-product-image]").forEach((img) => {
      img.addEventListener("error", () => {
        img.src = imageAsset("暫無產品圖片.png");
      }, { once: true });
    });
  }

  function brandDisplayName(product) {
    if (!product.brand_name) return product.company_name || "品牌未確認";
    return product.brand_is_fallback
      ? `${product.brand_name}（公司）`
      : product.brand_name;
  }

  function productCard(product) {
    return `<a data-testid="product-card" href="${url("product", { id: product.product_id, return_to: location.href })}"
      class="flex bg-white rounded-2xl overflow-hidden border border-border-light shadow-[0_4px_20px_rgb(0,0,0,0.02)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.05)] hover:scale-[1.01] active:scale-[0.98] transition-all duration-300 group min-h-[112px]">
      <div class="w-28 h-28 flex-shrink-0 bg-surface-container-low overflow-hidden relative">
        <img data-product-image class="w-full h-full object-contain group-hover:scale-105 transition-transform duration-500" src="${escapeHtml(productImage(product))}" alt="${escapeHtml(product.product_name)}" />
      </div>
      <div class="p-3.5 min-w-0 flex flex-col justify-between flex-grow">
        <div>
          <h3 class="font-headline-sm text-headline-sm text-on-surface truncate group-hover:text-primary transition-colors">${escapeHtml(product.product_name)}</h3>
          <p class="text-body-md text-text-muted truncate mt-0.5">${escapeHtml(brandDisplayName(product))}</p>
        </div>
        <div class="flex justify-between items-center gap-2">
          <span class="px-2.5 py-0.5 bg-primary-container/20 text-primary text-xs font-medium rounded-full truncate">${escapeHtml(product.category || "未分類")}</span>
          <span class="material-symbols-outlined text-outline text-[20px] group-hover:translate-x-1 transition-transform">chevron_right</span>
        </div>
      </div>
    </a>`;
  }

  function wireNavigation() {
    document.querySelectorAll("#bottom-nav").forEach((nav) => {
      if (nav.querySelector("#nav-products")) return;
      const productLink = document.createElement("a");
      productLink.id = "nav-products";
      productLink.className = "flex flex-col items-center justify-center px-2 sm:px-4 py-2 rounded-2xl text-on-surface-variant hover:text-primary transition-all duration-200 active:scale-90";
      productLink.innerHTML = '<span class="material-symbols-outlined text-[22px]">inventory_2</span><span class="text-[10px] font-medium mt-0.5">產品</span>';
      nav.querySelector("#nav-categories")?.after(productLink);
    });

    const destinations = {
      "首頁": url("home"),
      "大類": url("categories"),
      "品牌": url("list", { view: "brands" }),
      "公司": url("list", { view: "companies" }),
      "收藏": url("list", { view: "favorites" }),
    };
    // Wire bottom nav and any nav links by text label
    document.querySelectorAll("aside nav a, aside nav button").forEach((item) => {
      const text = item.textContent.replace(/\s+/g, "").trim();
      const label = Object.keys(destinations).find((name) => text.endsWith(name));
      const target = destinations[label];
      if (!target) return;
      if (item.tagName === "A") item.href = target;
      else item.addEventListener("click", () => location.href = target);
    });
    // Wire bottom nav by id
    const bottomNavMap = {
      "nav-home": url("home"),
      "nav-categories": url("categories"),
      "nav-products": url("list", { view: "products" }),
      "nav-brands": url("list", { view: "brands" }),
      "nav-favorites": url("list", { view: "favorites" }),
    };
    Object.entries(bottomNavMap).forEach(([id, href]) => {
      const el = document.getElementById(id);
      if (el) el.href = href;
    });
    // Wire info page links — both source and disclaimer now go to the combined page
    document.querySelectorAll("a").forEach((item) => {
      const label = item.textContent.replace(/\s+/g, "").trim();
      if (label.includes("資料說明及免責聲明") || label.includes("資料來源說明") || label === "資料來源" || label === "資料說明") item.href = url("source");
      if (label.includes("免責聲明")) item.href = url("source");
    });
  }

  function setBrandLogo() {
    document.querySelectorAll("[data-brand-header]").forEach((container) => {
      // Show unified banner logo in header
      const bannerUrl = imageAsset("橫幅.png");
      container.className = "flex items-center flex-none shrink-0 overflow-visible";
      container.innerHTML = `
        <img src="${bannerUrl}" alt="溯食光" class="h-8 w-auto object-contain object-left" style="max-width:180px" />
      `;
    });
    document.querySelectorAll(".year-footer, #year-footer").forEach((el) => {
      el.textContent = new Date().getFullYear();
    });
  }

  function highlightActiveTab() {
    const params = new URLSearchParams(location.search);
    const view = params.get("view");
    let activeId = null;

    if (page === "home") {
      activeId = "nav-home";
    } else if (page === "categories") {
      activeId = "nav-categories";
    } else if (page === "list") {
      if (!view || view === "products") activeId = "nav-products";
      else if (view === "brands") activeId = "nav-brands";
      else if (view === "favorites") activeId = "nav-favorites";
    }

    const ids = ["nav-home", "nav-categories", "nav-products", "nav-brands", "nav-favorites"];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const icon = el.querySelector(".material-symbols-outlined");
      if (id === activeId) {
        el.className = "flex flex-col items-center justify-center px-2 sm:px-4 py-2 rounded-2xl bg-primary text-white transition-all duration-200 active:scale-90";
        if (icon) icon.style.fontVariationSettings = "'FILL' 1";
      } else {
        el.className = "flex flex-col items-center justify-center px-2 sm:px-4 py-2 rounded-2xl text-on-surface-variant hover:text-primary transition-all duration-200 active:scale-90";
        if (icon) icon.style.fontVariationSettings = "'FILL' 0";
      }
    });
  }

  async function renderHome() {
    const main = document.querySelector("main");
    main.innerHTML = `<section class="hidden md:block relative">
      <form data-testid="home-search" class="flex items-center bg-white border border-border-light rounded-full px-5 py-3.5 shadow-[0_4px_20px_rgb(0,0,0,0.02)] focus-within:shadow-[0_8px_30px_rgb(0,0,0,0.05)] focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-all duration-300">
        <span class="material-symbols-outlined text-outline mr-3">search</span>
        <input name="q" class="w-full bg-transparent border-none focus:ring-0 text-body-lg p-0 outline-none placeholder:text-outline/55" placeholder="搜尋產品、品牌或公司" />
      </form>
    </section>
    <section class="space-y-3">
      <div class="flex justify-between items-end mb-2"><h2 class="font-headline-md text-headline-md text-on-surface font-semibold">探索大類</h2><a class="text-primary font-label-lg hover:underline" href="${url("categories")}">查看全部</a></div>
      <div id="home-categories" class="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3 px-1">${loading()}</div>
    </section>
    <section class="bg-surface-container-low/60 backdrop-blur-sm -mx-6 px-6 py-6 rounded-2xl border border-border-light/40 space-y-4 md:mx-0 md:px-6">
      <h2 class="font-headline-md text-headline-md text-on-surface font-semibold">熱門品牌</h2>
      <div id="home-brands" class="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3 px-1">${loading()}</div>
    </section>
    <section class="space-y-4">
      <div class="flex justify-between items-center"><h2 class="font-headline-md text-headline-md text-on-surface font-semibold">最近查看</h2><a href="${url("list", { view: "favorites" })}" class="text-primary text-sm font-semibold hover:underline">我的收藏</a></div>
      <div id="home-recent" class="grid grid-cols-1 xl:grid-cols-2 gap-4 w-full min-w-0">${loading()}</div>
    </section>`;

    const searchForm = main.querySelector("form");
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const q = new FormData(event.currentTarget).get("q").trim();
      if (q) location.href = url("list", { view: "products", q });
    });
    searchForm.querySelector("input").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        searchForm.requestSubmit();
      }
    });

    const categoryBox = document.getElementById("home-categories");
    const brandBox = document.getElementById("home-brands");
    const recentBox = document.getElementById("home-recent");
    try {
      const [categories, brands, recent] = await Promise.all([
        api("/api/categories", { client: false }),
        api("/api/brands/popular?limit=8", { client: false }),
        api("/api/recently-viewed?page_size=4"),
      ]);
      categoryBox.innerHTML = categories.items.slice(0, 8).map((item) => `<a href="${url("list", { view: "category_brands", category_id: item.category_id, title: item.name })}" class="flex flex-col items-center justify-center group min-w-0 min-h-[120px] text-center bg-white border border-border-light rounded-xl px-3 py-3.5 hover:border-primary/50 hover:shadow-sm transition-all active:scale-[0.98]">
        <div class="w-14 h-14 rounded-2xl bg-primary-container/40 flex items-center justify-center mb-2 group-hover:scale-105 transition-transform"><span class="material-symbols-outlined text-primary text-3xl">${getCategoryIcon(item.name)}</span></div>
        <p class="text-sm text-on-surface font-semibold leading-snug break-words w-full group-hover:text-primary transition-colors">${escapeHtml(item.name)}</p>
      </a>`).join("");
      brandBox.innerHTML = brands.items.map((item) => `<a href="${url("list", { view: "brand_categories", brand_id: item.brand_id, title: item.name })}" class="flex items-center justify-center py-2 px-2.5 bg-white border-2 border-outline/20 rounded-full shadow-[0_2px_8px_rgba(0,0,0,0.01)] hover:border-primary hover:bg-primary/5 active:scale-95 transition-all duration-200 min-h-[42px] group min-w-0 overflow-hidden">
        <span class="font-bold text-on-surface group-hover:text-primary w-full text-center text-sm sm:text-base break-all leading-tight">${escapeHtml(item.name)}</span>
      </a>`).join("");
      recentBox.className = recent.items.length
        ? "grid grid-cols-1 xl:grid-cols-2 gap-4 w-full min-w-0"
        : "w-full";
      recentBox.innerHTML = recent.items.length
        ? recent.items.map(productCard).join("")
        : emptyState("還沒有瀏覽紀錄", "查看產品後會自動出現在這裡", url("list", { view: "products" }), "開始探索");
      attachImageFallback(main);
    } catch (error) {
      categoryBox.className = "w-full mb-6";
      categoryBox.innerHTML = errorState(error, renderHome);
      brandBox.innerHTML = "";
      recentBox.innerHTML = "";
    }
  }

  async function renderCategories() {
    const main = document.querySelector("main");
    main.innerHTML = `<section class="max-w-7xl mx-auto">
      <div class="flex items-end justify-between gap-4"><div><h2 class="font-headline-lg text-headline-lg text-on-surface font-semibold">所有 <span class="text-secondary ml-1">食品大類</span></h2><div class="w-16 h-1 bg-primary mt-2 rounded-full"></div></div><span id="category-total" class="text-text-muted whitespace-nowrap"></span></div>
      <div class="flex items-center bg-white border border-border-light rounded-full px-5 py-3.5 shadow-[0_4px_20px_rgb(0,0,0,0.02)] focus-within:shadow-[0_8px_30px_rgb(0,0,0,0.05)] focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10 transition-all duration-300 mt-6">
        <span class="material-symbols-outlined text-outline mr-3">search</span>
        <input data-testid="category-search" class="w-full bg-transparent border-none focus:ring-0 text-body-lg p-0 outline-none placeholder:text-outline/55" placeholder="搜尋大類名稱…" />
      </div>
      <div id="category-grid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-3 mt-6">${loading()}</div>
    </section>`;
    const grid = document.getElementById("category-grid");
    try {
      const data = await api("/api/categories", { client: false });
      document.getElementById("category-total").textContent = `共 ${data.items.length} 個大類`;
      const draw = (keyword = "") => {
        const filtered = data.items.filter((item) => item.name.includes(keyword.trim()));
        grid.innerHTML = filtered.map((item) => `<a data-category-name="${escapeHtml(item.name)}" href="${url("list", { view: "category_brands", category_id: item.category_id, title: item.name })}" class="bg-white rounded-xl border border-border-light shadow-sm p-3.5 min-h-32 flex flex-col gap-3 hover:border-primary/50 hover:shadow-md transition-all active:scale-[0.98]">
          <span class="material-symbols-outlined text-primary text-3xl">${getCategoryIcon(item.name)}</span>
          <div class="mt-auto"><h3 class="font-semibold text-sm leading-snug">${escapeHtml(item.name)}</h3><div class="flex flex-wrap gap-x-2 mt-1.5"><p class="text-xs text-text-muted">${item.product_count.toLocaleString()} 項產品</p><p class="text-xs text-secondary">${item.brand_count.toLocaleString()} 個品牌</p></div></div>
        </a>`).join("") || `<div class="col-span-full">${emptyState("找不到大類", "請換一個關鍵字")}</div>`;
      };
      draw();
      main.querySelector("input").addEventListener("input", (event) => draw(event.target.value));
    } catch (error) {
      grid.innerHTML = `<div class="col-span-full">${errorState(error, renderCategories)}</div>`;
    }
  }

  const nutritionLabels = [
    ["kcal", "熱量", "大卡"], ["protein", "蛋白質", "公克"], ["fat", "脂肪", "公克"],
    ["saturated_fat", "飽和脂肪", "公克"], ["trans_fat", "反式脂肪", "公克"],
    ["carbs", "碳水化合物", "公克"], ["sugar", "糖", "公克"], ["sodium", "鈉", "毫克"],
  ];

  function nutritionRows(nutrition) {
    const hasGram = nutritionLabels.some(([key]) => nutrition[`${key}_100g`]);
    const suffix = hasGram ? "100g" : "100ml";
    return nutritionLabels.map(([key, label, unit], index) => {
      const raw = nutrition[`${key}_${suffix}`];
      const display = raw ? `${escapeHtml(raw)}${String(raw).match(/[A-Za-z\u4e00-\u9fff]/) ? "" : ` ${unit}`}` : "未提供";
      return `<tr class="${index % 2 ? "bg-surface-container-lowest" : ""}"><td class="px-5 py-3">${label}</td><td class="px-5 py-3 font-bold text-right ${raw ? "" : "text-outline italic font-normal"}">${display}</td></tr>`;
    }).join("");
  }

  async function renderProduct() {
    const main = document.querySelector("main");
    const id = new URLSearchParams(location.search).get("id");
    if (!id) {
      main.innerHTML = emptyState("沒有指定產品", "請從產品列表選擇一項產品");
      return;
    }
    main.innerHTML = loading("正在讀取產品資料…");
    try {
      const data = await api(`/api/products/${encodeURIComponent(id)}`);
      const p = data.product;
      const n = data.nutrition;
      main.innerHTML = `
      <section class="max-w-5xl mx-auto px-1 mb-6">
        <h2 class="font-headline-lg text-headline-lg text-on-surface font-semibold">產品 <span class="text-secondary ml-1">詳細資料</span></h2>
        <div class="w-16 h-1 bg-primary mt-2 rounded-full"></div>
      </section>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start max-w-5xl mx-auto px-1 mt-4">
        <!-- Left Column: Product Image & Basic Info (lg:col-span-5) -->
        <div class="lg:col-span-5 space-y-6">
          <div class="aspect-square bg-white rounded-2xl overflow-hidden border border-border-light shadow-[0_4px_24px_rgba(0,0,0,0.02)] flex items-center justify-center">
            <img data-product-image class="w-full h-full object-contain hover:scale-102 transition-transform duration-500" src="${escapeHtml(productImage(p))}" alt="${escapeHtml(p.product_name)}" />
          </div>
          <div class="space-y-3 bg-white p-5 rounded-2xl border border-border-light shadow-[0_4px_24px_rgba(0,0,0,0.02)]">
            <div class="flex flex-wrap gap-2">
              <span class="px-2.5 py-1 bg-primary text-white text-xs font-semibold rounded-full">${escapeHtml(p.category || "未分類")}</span>
              ${p.brand_name ? `<span class="px-2.5 py-1 bg-primary-container/20 text-primary text-xs font-semibold rounded-full">${escapeHtml(brandDisplayName(p))}</span>` : '<span class="px-2.5 py-1 bg-surface-container text-text-muted text-xs font-semibold rounded-full">品牌未確認</span>'}
            </div>
            <h1 class="text-2xl font-bold text-on-surface leading-snug">${escapeHtml(p.product_name)}</h1>
            <p class="text-on-surface-variant font-medium">${escapeHtml(p.company_name || "公司未提供")}</p>
            <p class="text-xs text-text-muted mt-1">包裝規格：${escapeHtml(p.package || "未提供")}</p>
          </div>
        </div>

        <!-- Right Column: Traceability, Warning & Nutrition Table (lg:col-span-7) -->
        <div class="lg:col-span-7 space-y-6">
          <!-- Traceability -->
          <div class="bg-surface-container-low/60 border border-border-light rounded-xl px-4 py-3">
            <p class="text-xs text-text-muted font-medium">食品追溯碼</p>
            <p class="text-sm text-on-surface-variant font-medium mt-1 break-all leading-relaxed">${escapeHtml(p.trace_code || "未提供")}</p>
          </div>

          <!-- Warning -->
          ${p.warning ? `<div class="bg-warning-surface border border-warning/30 rounded-2xl p-5 flex gap-3 shadow-sm">
            <span class="material-symbols-outlined text-warning shrink-0">warning</span>
            <div>
              <h3 class="font-bold text-warning text-sm">過敏原資訊 / 警語</h3>
              <p class="text-sm mt-1 text-on-secondary-container leading-relaxed">${escapeHtml(p.warning)}</p>
            </div>
          </div>` : ""}

          <!-- Nutrition -->
          <div class="space-y-3">
            <h2 class="text-lg font-bold text-on-surface flex items-center gap-2 px-1">
              <span class="material-symbols-outlined text-primary">nutrition</span>營養標示
            </h2>
            <div class="bg-white rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-border-light overflow-hidden">
              <div class="p-5 bg-surface-container-low/50 border-b border-border-light">
                <p class="text-sm text-on-surface-variant font-medium">每一份量 ${escapeHtml(n.serving_size || "未提供")}</p>
                <p class="text-sm text-on-surface-variant font-medium mt-0.5">本包裝含 ${escapeHtml(n.servings_per_package || "未提供")} 份</p>
              </div>
              <table class="w-full text-sm">
                <thead>
                  <tr class="bg-surface-container-high/40 border-b border-border-light text-on-surface font-semibold">
                    <th class="px-5 py-3 text-left">項目</th>
                    <th class="px-5 py-3 text-right">每 100 公克／毫升</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-light">${nutritionRows(n)}</tbody>
              </table>
            </div>
          </div>

          <!-- Actions & Footer -->
          <div class="flex flex-col items-center gap-4 py-6 border border-border-light bg-white rounded-2xl p-5 shadow-sm">
            <button data-testid="favorite-button" class="flex items-center justify-center gap-2 px-8 py-3 bg-white border border-primary text-primary hover:bg-primary/5 rounded-full font-semibold transition-all active:scale-95 duration-150 min-h-[44px]">
              <span class="material-symbols-outlined" style="font-variation-settings:'FILL' ${data.is_favorite ? 1 : 0}">favorite</span>
              <span>${data.is_favorite ? "已收藏" : "加入收藏"}</span>
            </button>
          </div>
        </div>
      </div>`;
      attachImageFallback(main);
      const favorite = main.querySelector("[data-testid='favorite-button']");
      favorite.addEventListener("click", async () => {
        favorite.disabled = true;
        try {
          const active = favorite.querySelector("span:last-child").textContent === "已收藏";
          await api(`/api/favorites/${p.product_id}`, { method: active ? "DELETE" : "POST" });
          favorite.querySelector("span:last-child").textContent = active ? "加入收藏" : "已收藏";
          favorite.querySelector(".material-symbols-outlined").style.fontVariationSettings = `'FILL' ${active ? 0 : 1}`;
          toast(active ? "已移除收藏" : "已加入收藏");
        } catch (error) { toast(error.message); }
        finally { favorite.disabled = false; }
      });
    } catch (error) {
      main.innerHTML = errorState(error, renderProduct);
    }
  }

  async function renderCombinedInfo() {
    const main = document.querySelector("main");
    main.innerHTML = loading("正在讀取資料…");
    try {
      const meta = await api("/api/meta/source", { client: false });
      const updated = new Intl.DateTimeFormat("zh-TW", { dateStyle: "long", timeStyle: "short", timeZone: "Asia/Taipei" }).format(new Date(meta.database_last_imported_at || meta.source_file_modified_at));
      main.innerHTML = `${infoLogo()}
        <section class="bg-white rounded-2xl p-5 shadow-sm border border-border-light space-y-3">
          <div class="flex items-center gap-2"><span class="material-symbols-outlined text-primary">database</span><h2 class="font-semibold text-base text-primary">資料來源說明</h2></div>
          <p class="text-on-surface-variant text-sm leading-relaxed">本平台之食品資料均來源於「${escapeHtml(meta.source_name)}」，我們針對資料進行清洗、結構化與分類展示，以便大眾便捷查詢。</p>
          <a class="flex items-center justify-between p-3.5 bg-surface-container-low hover:bg-primary-container/20 rounded-xl text-primary text-sm font-semibold transition-all active:scale-[0.98]" href="${escapeHtml(meta.source_url)}" target="_blank" rel="noopener noreferrer">
            <span>前往政府資料開放平臺查看原始數據</span>
            <span class="material-symbols-outlined text-[18px]">open_in_new</span>
          </a>
          <p class="text-text-muted text-xs">資料最後更新：${escapeHtml(updated)}</p>
        </section>
        <section class="bg-disclaimer-surface rounded-2xl p-5 shadow-sm border border-warning/20 space-y-3">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-warning" style="font-variation-settings:'FILL' 1">warning</span>
            <h2 class="font-semibold text-base text-warning">免責聲明</h2>
          </div>
          <p class="leading-relaxed text-on-secondary-container text-sm">${escapeHtml(meta.disclaimer)}</p>
          <p class="leading-relaxed text-on-secondary-container text-xs opacity-80">所有的食品成分標示、追溯資訊與警語，請以產品外包裝或官方機構最新公告為基準。本平台提供之數據僅供大眾參考，不構成任何醫療、營養或食品安全建議。</p>
        </section>
        <div class="text-center"><p class="text-text-muted text-xs">資料最後更新：${escapeHtml(updated)}</p></div>
        <div class="flex justify-center pt-2">
          <button onclick="history.length > 1 ? history.back() : (location.href = '${url('home')}')" class="flex items-center gap-2 px-8 py-3 bg-primary text-white rounded-full font-semibold shadow-md hover:bg-on-primary-container active:scale-95 transition-all min-h-[44px]">
            <span class="material-symbols-outlined text-[18px]">arrow_back</span>返回前頁
          </button>
        </div>`;
    } catch (error) {
      main.innerHTML = errorState(error, renderCombinedInfo);
    }
  }

  function infoLogo() {
    // Display square logo, centered — matches user's request
    return `<div class="flex flex-col items-center gap-3 py-6">
      <img src="${imageAsset("方形LOGO.png")}" alt="溯食光 Logo" class="w-96 h-96 object-contain" />
    </div>`;
  }

  // Both source and disclaimer now show the same combined page
  async function renderSource() { return renderCombinedInfo(); }
  async function renderDisclaimer() { return renderCombinedInfo(); }

  function renderListCard(item, view, params = new URLSearchParams(location.search)) {
    if (view === "brands") {
      return `<a href="${url("list", { view: "brand_categories", brand_id: item.brand_id, title: item.name })}" class="bg-white border rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all duration-200">
        <div class="min-w-0">
          <h2 class="font-bold text-lg text-on-surface truncate">${escapeHtml(item.name)}</h2>
          <p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品・${item.category_count} 個大類</p>
        </div>
        <span class="material-symbols-outlined text-primary">chevron_right</span>
      </a>`;
    }
    if (view === "companies") {
      return `<a href="${url("list", { view: "company_brands", company_id: item.company_id, title: item.name })}" class="bg-white border rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all duration-200"><div class="min-w-0"><h2 class="font-bold text-lg truncate text-on-surface">${escapeHtml(item.name)}</h2><p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品・${item.brand_count} 個品牌</p></div><span class="material-symbols-outlined text-primary">chevron_right</span></a>`;
    }
    if (view === "category_brands") {
      const categoryId = params.get("category_id");
      const categoryTitle = params.get("title") || "大類";
      return `<a href="${url("list", { view: "products", category_id: categoryId, brand_id: item.brand_id, title: item.name, category_title: categoryTitle })}" class="bg-white border border-border-light rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all"><div><h2 class="font-bold text-lg text-on-surface">${escapeHtml(item.name)}</h2><p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品</p></div><span class="material-symbols-outlined text-primary">chevron_right</span></a>`;
    }
    if (view === "brand_categories") {
      const brandId = params.get("brand_id");
      const brandTitle = params.get("title") || "品牌";
      return `<a href="${url("list", { view: "products", brand_id: brandId, category_id: item.category_id, title: item.name, brand_title: brandTitle })}" class="bg-white border border-border-light rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all"><div><h2 class="font-bold text-lg text-on-surface">${escapeHtml(item.name)}</h2><p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品</p></div><span class="material-symbols-outlined text-primary">chevron_right</span></a>`;
    }
    if (view === "company_brands") {
      const companyId = params.get("company_id");
      const companyTitle = params.get("title") || "公司";
      return `<a href="${url("list", { view: "company_brand_categories", company_id: companyId, brand_id: item.brand_id, title: item.name, company_title: companyTitle })}" class="bg-white border border-border-light rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all"><div><h2 class="font-bold text-lg text-on-surface">${escapeHtml(item.name)}</h2><p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品</p></div><span class="material-symbols-outlined text-primary">chevron_right</span></a>`;
    }
    if (view === "company_brand_categories") {
      const companyId = params.get("company_id");
      const brandId = params.get("brand_id");
      const companyTitle = params.get("company_title") || "公司";
      const brandTitle = params.get("title") || "品牌";
      return `<a href="${url("list", { view: "products", company_id: companyId, brand_id: brandId, category_id: item.category_id, title: item.name, company_title: companyTitle, brand_title: brandTitle })}" class="bg-white border border-border-light rounded-xl p-5 flex justify-between items-center hover:border-primary/50 hover:shadow-sm transition-all"><div><h2 class="font-bold text-lg text-on-surface">${escapeHtml(item.name)}</h2><p class="text-sm text-text-muted mt-1">${item.product_count.toLocaleString()} 項產品</p></div><span class="material-symbols-outlined text-primary">chevron_right</span></a>`;
    }
    return productCard(item);
  }

  function pageHref(pageNumber) {
    const target = new URL(location.href);
    target.searchParams.set("view", "products");
    target.searchParams.set("page", String(pageNumber));
    return target.href;
  }

  function paginationItems(currentPage, totalPages) {
    const pages = new Set([1, totalPages]);
    for (let number = currentPage - 2; number <= currentPage + 2; number += 1) {
      if (number > 0 && number <= totalPages) pages.add(number);
    }
    const sorted = [...pages].sort((a, b) => a - b);
    const items = [];
    sorted.forEach((number, index) => {
      if (index > 0 && number - sorted[index - 1] > 1) items.push(null);
      items.push(number);
    });
    return items;
  }

  function renderPagination(container, pagination) {
    const currentPage = pagination.page;
    const totalPages = pagination.total_pages;
    if (!totalPages) {
      container.innerHTML = "";
      container.classList.add("hidden");
      return;
    }

    const pageButtons = paginationItems(currentPage, totalPages).map((number) => {
      if (number === null) return '<span class="px-1 text-text-muted" aria-hidden="true">…</span>';
      const active = number === currentPage;
      return `<a href="${pageHref(number)}" ${active ? 'aria-current="page"' : ""}
        class="min-w-10 h-10 px-3 inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-colors ${active ? "bg-primary text-white" : "bg-white border border-border-light text-on-surface hover:border-primary hover:text-primary"}">${number}</a>`;
    }).join("");

    container.classList.remove("hidden");
    container.innerHTML = `
      <p class="text-sm text-text-muted text-center">第 ${currentPage.toLocaleString()}／${totalPages.toLocaleString()} 頁・共 ${pagination.total.toLocaleString()} 筆產品</p>
      <div class="flex items-center justify-center gap-2 flex-wrap">
        ${currentPage > 1 ? `<a href="${pageHref(currentPage - 1)}" class="h-10 px-4 inline-flex items-center gap-1 rounded-xl bg-white border border-border-light text-sm font-semibold hover:border-primary hover:text-primary"><span class="material-symbols-outlined text-lg">chevron_left</span>上一頁</a>` : '<span class="h-10 px-4 inline-flex items-center gap-1 rounded-xl bg-surface-container text-outline text-sm font-semibold opacity-60"><span class="material-symbols-outlined text-lg">chevron_left</span>上一頁</span>'}
        ${pageButtons}
        ${currentPage < totalPages ? `<a href="${pageHref(currentPage + 1)}" class="h-10 px-4 inline-flex items-center gap-1 rounded-xl bg-white border border-border-light text-sm font-semibold hover:border-primary hover:text-primary">下一頁<span class="material-symbols-outlined text-lg">chevron_right</span></a>` : '<span class="h-10 px-4 inline-flex items-center gap-1 rounded-xl bg-surface-container text-outline text-sm font-semibold opacity-60">下一頁<span class="material-symbols-outlined text-lg">chevron_right</span></span>'}
      </div>`;
  }

  async function renderList() {
    const params = new URLSearchParams(location.search);
    const view = params.get("view") || "products";
    const queryText = (params.get("q") || "").trim();
    const requestedPage = Math.max(1, Number.parseInt(params.get("page") || "1", 10) || 1);
    
    // Set dynamic page title in <main>
    const titleEl = document.getElementById("list-main-title");
    if (titleEl) {
      let displayTitle = "所有 <span class='text-secondary ml-1'>食品</span>";
      if (view === "brands") {
        displayTitle = queryText
          ? "<span class='text-secondary mr-1'>品牌</span> 搜尋"
          : "所有 <span class='text-secondary ml-1'>品牌</span>";
      } else if (view === "companies") {
        displayTitle = queryText
          ? "<span class='text-secondary mr-1'>公司</span> 搜尋"
          : "所有 <span class='text-secondary ml-1'>公司</span>";
      } else if (view === "favorites") {
        displayTitle = "我的 <span class='text-secondary ml-1'>收藏</span>";
      } else if (view === "category_brands") {
        const catTitle = params.get("title") || "大類";
        displayTitle = `${catTitle} 的 <span class='text-secondary ml-1'>品牌</span>`;
      } else if (view === "brand_categories") {
        const brandTitle = params.get("title") || "品牌";
        displayTitle = `${brandTitle} 的 <span class='text-secondary ml-1'>大類</span>`;
      } else if (view === "company_brands") {
        const compTitle = params.get("title") || "公司";
        displayTitle = `${compTitle} 的 <span class='text-secondary ml-1'>品牌</span>`;
      } else if (view === "company_brand_categories") {
        const compTitle = params.get("company_title") || "公司";
        const brandTitle = params.get("title") || "品牌";
        displayTitle = `${compTitle} - ${brandTitle} 的 <span class='text-secondary ml-1'>大類</span>`;
      } else if (view === "products") {
        const compId = params.get("company_id");
        const brandId = params.get("brand_id");
        const catId = params.get("category_id");
        if (compId && brandId && catId) {
          const compTitle = params.get("company_title") || "公司";
          const brandTitle = params.get("brand_title") || "品牌";
          const catTitle = params.get("title") || "大類";
          displayTitle = `${compTitle} - ${brandTitle} 的 <span class='text-secondary ml-1'>${catTitle}</span>`;
        } else if (catId && brandId) {
          if (params.get("category_title")) {
            const catTitle = params.get("category_title");
            const brandTitle = params.get("title") || "品牌";
            displayTitle = `${catTitle} 的 <span class='text-secondary ml-1'>${brandTitle}</span>`;
          } else if (params.get("brand_title")) {
            const brandTitle = params.get("brand_title");
            const catTitle = params.get("title") || "大類";
            displayTitle = `${brandTitle} 的 <span class='text-secondary ml-1'>${catTitle}</span>`;
          }
        } else {
          displayTitle = params.get("q") ? `搜尋「<span class='text-secondary'>${params.get("q")}</span>」` : "所有 <span class='text-secondary ml-1'>產品</span>";
        }
      }
      titleEl.innerHTML = displayTitle;
    }

    // Dynamic Back Button Logic
    const backBtn = document.querySelector("[data-back-button]");
    const isUnfilteredProducts = view === "products" && !["q", "category_id", "brand_id"].some((key) => params.get(key));
    const isTopLevel = ["brands", "favorites"].includes(view) || isUnfilteredProducts;
    if (backBtn) {
      if (isTopLevel) {
        backBtn.classList.add("hidden");
      } else {
        backBtn.classList.remove("hidden");
        let backUrl = url("home");
        if (view === "category_brands") {
          backUrl = url("categories");
        } else if (view === "brand_categories") {
          backUrl = url("list", { view: "brands" });
        } else if (view === "products") {
          const brandId = params.get("brand_id");
          const categoryId = params.get("category_id");
          
          if (categoryId && brandId) {
            if (params.get("category_title")) {
              const categoryTitle = params.get("category_title");
              backUrl = url("list", { view: "category_brands", category_id: categoryId, title: categoryTitle });
            } else if (params.get("brand_title")) {
              const brandTitle = params.get("brand_title");
              backUrl = url("list", { view: "brand_categories", brand_id: brandId, title: brandTitle });
            }
          }
        }
        backBtn.href = backUrl;
        backBtn.removeAttribute("onclick");
      }
    }

    const form = document.querySelector("[data-search-form]");
    const input = form.querySelector("input");

    const usesLocalSearch = ["favorites", "category_brands", "brand_categories"].includes(view);

    if (view === "favorites") {
      input.placeholder = "搜尋收藏的產品名稱…";
    } else if (view === "brands") {
      input.placeholder = "搜尋品牌";
    } else if (view === "category_brands") {
      input.placeholder = "搜尋品牌名稱…";
    } else if (view === "brand_categories") {
      input.placeholder = "搜尋大類名稱…";
    } else {
      input.placeholder = "搜尋產品或品牌";
    }

    input.value = params.get("q") || "";
    const clearSearch = document.querySelector("[data-clear-search]");
    if (clearSearch && queryText) {
      clearSearch.classList.remove("hidden");
      clearSearch.classList.add("flex");
      clearSearch.addEventListener("click", () => {
        if (view === "products") {
          const target = new URL(location.href);
          target.searchParams.delete("q");
          target.searchParams.set("page", "1");
          location.href = target.href;
        } else {
          location.href = url("list", { view });
        }
      });
    }

    const box = document.querySelector("[data-list-content]");
    let paginationBox = document.querySelector("[data-pagination]");
    if (!paginationBox) {
      paginationBox = document.createElement("nav");
      paginationBox.dataset.pagination = "";
      paginationBox.setAttribute("aria-label", "產品分頁");
      paginationBox.className = "hidden mt-8 mb-4 space-y-3";
      box.after(paginationBox);
    }
    const resultHeader = document.querySelector("[data-result-header]");
    const resultHeading = document.querySelector("[data-result-heading]");
    const titleCount = document.querySelector("[data-title-count]");
    const isFavorites = view === "favorites";
    const waitsForSearch = false;
    // Favorites: hide result header until user types; others: show by default
    resultHeader?.classList.toggle("hidden", isFavorites);
    if (["brands", "companies"].includes(view) && resultHeading) {
      resultHeading.textContent = queryText ? "搜尋結果" : "熱門推薦";
    }
    let allItems = [];

    const draw = (keyword = "") => {
      const filtered = allItems.filter((item) => {
        const name = item.product_name || item.name || "";
        return name.toLowerCase().includes(keyword.trim().toLowerCase());
      });
      if (isFavorites) {
        const hasKeyword = keyword.trim().length > 0;
        // Show result header (搜尋結果) only when user has typed something
        if (hasKeyword) {
          resultHeader?.classList.remove("hidden");
          document.querySelector("[data-result-count]").textContent = `${filtered.length} 筆結果`;
          if (resultHeading) resultHeading.textContent = "搜尋結果";
        } else {
          resultHeader?.classList.add("hidden");
        }
        box.className = filtered.length ? "grid grid-cols-1 md:grid-cols-2 gap-4" : "w-full";
        if (filtered.length) {
          box.innerHTML = filtered.map((item) => renderListCard(item, view, params)).join("");
        } else if (hasKeyword) {
          // Search returned nothing
          box.innerHTML = emptyState("找不到符合的收藏項目", "請嘗試更換搜尋關鍵字", null);
        } else {
          // No favorites at all
          box.innerHTML = emptyState("目前沒有收藏項目", "收藏您感興趣的產品，下次可快速查閱", null);
        }
      } else {
        document.querySelector("[data-result-count]").textContent = `${filtered.length} 筆結果`;
        box.className = filtered.length ? "grid grid-cols-1 md:grid-cols-2 gap-4" : "w-full";
        box.innerHTML = filtered.length
          ? filtered.map((item) => renderListCard(item, view, params)).join("")
          : emptyState("目前沒有資料", "請調整搜尋條件再試一次");
      }
      attachImageFallback(box);
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const q = input.value.trim();
      if (usesLocalSearch) {
        draw(q);
      } else if (view === "products") {
        const target = new URL(location.href);
        if (q) target.searchParams.set("q", q);
        else target.searchParams.delete("q");
        target.searchParams.set("view", "products");
        target.searchParams.set("page", "1");
        location.href = target.href;
      } else {
        location.href = url("list", { view, q });
      }
    });

    input.addEventListener("input", (event) => {
      if (usesLocalSearch) {
        draw(event.target.value);
      }
    });

    try {
      let path;
      if (view === "brands") {
        path = queryText
          ? `/api/brands?page_size=100&q=${encodeURIComponent(queryText)}`
          : "/api/brands/popular?limit=20";
      }
      else if (view === "category_brands") path = `/api/categories/${encodeURIComponent(params.get("category_id"))}/brands`;
      else if (view === "brand_categories") path = `/api/brands/${encodeURIComponent(params.get("brand_id"))}/categories`;
      else if (view === "favorites") path = "/api/favorites?page_size=100";
      else {
        const query = new URLSearchParams({ page: String(requestedPage), page_size: "50" });
        ["q", "category_id", "brand_id"].forEach((key) => { if (params.get(key)) query.set(key, params.get(key)); });
        path = `/api/products?${query}`;
      }
      const data = await api(path, { client: view === "favorites" });
      allItems = data.items || [];

      if (view === "products" && data.pagination) {
        const totalPages = data.pagination.total_pages;
        if (totalPages > 0 && requestedPage > totalPages) {
          location.replace(pageHref(totalPages));
          return;
        }
        renderPagination(paginationBox, data.pagination);
      } else {
        paginationBox.classList.add("hidden");
        paginationBox.innerHTML = "";
      }

      if (!queryText && titleCount && data.pagination) {
        if (view === "brands") {
          titleCount.textContent = `共 ${data.pagination.total.toLocaleString()} 個品牌`;
          titleCount.classList.remove("hidden");
        } else {
          titleCount.classList.add("hidden");
        }
      } else if (titleCount) {
        titleCount.classList.add("hidden");
      }

      if (usesLocalSearch) {
        draw(input.value);
      } else {
        const count = (!queryText && view === "brands")
          ? allItems.length
          : (data.pagination?.total ?? allItems.length);
        document.querySelector("[data-result-count]").textContent = `${count} 筆結果`;
        box.className = allItems.length
          ? "grid grid-cols-1 md:grid-cols-2 gap-4"
          : "w-full";
        box.innerHTML = allItems.length ? allItems.map((item) => renderListCard(item, view, params)).join("") : emptyState("目前沒有資料", "請調整搜尋條件再試一次");
        attachImageFallback(box);
      }

      // Show info footer link for favorites page
      if (isFavorites) {
        const infoFooter = document.getElementById("favorites-info-footer");
        if (infoFooter) {
          infoFooter.classList.remove("hidden");
          const infoLink = infoFooter.querySelector("a");
          if (infoLink) infoLink.href = url("source");
        }
      }
    } catch (error) {
      box.className = "w-full";
      box.innerHTML = errorState(error, renderList);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    setBrandLogo();
    wireNavigation();
    highlightActiveTab();

    const handlers = { home: renderHome, categories: renderCategories, product: renderProduct, source: renderSource, disclaimer: renderDisclaimer, list: renderList };
    handlers[page]?.();
  });
})();
