// ShortX Frontend Application Logic
(function() {
  const API_BASE = "";

  const state = {
    token: localStorage.getItem("shortx_token") || null,
    user: null,
    authMode: "signup", // "signup" or "login"
    urls: [],
    stats: { total_links: 0, total_clicks: 0, active_links: 0 },
    activeAnalyticsUrl: null
  };

  // DOM Elements
  const el = {
    appHeader: document.querySelector(".app-header"),
    userNav: document.getElementById("user-nav"),
    navGreeting: document.getElementById("nav-user-greeting"),
    logoutBtn: document.getElementById("logout-btn"),
    brandLink: document.getElementById("brand-link"),

    // Views
    authView: document.getElementById("auth-view"),
    dashboardView: document.getElementById("dashboard-view"),
    analyticsView: document.getElementById("analytics-view"),

    // Auth Form
    authForm: document.getElementById("auth-form"),
    authEmail: document.getElementById("auth-email"),
    authPassword: document.getElementById("auth-password"),
    authSubtitle: document.getElementById("auth-subtitle"),
    authSubmitBtn: document.getElementById("auth-submit-btn"),
    authSwitchBtn: document.getElementById("auth-switch-btn"),
    authSwitchText: document.getElementById("auth-switch-text"),

    // Dashboard
    dashboardGreeting: document.getElementById("dashboard-greeting"),
    shortenForm: document.getElementById("shorten-form"),
    urlInput: document.getElementById("url-input"),
    btnShorten: document.getElementById("btn-shorten"),
    createdBanner: document.getElementById("created-banner"),
    createdShortLink: document.getElementById("created-short-link"),
    btnCopyCreated: document.getElementById("btn-copy-created"),
    statTotalLinks: document.getElementById("stat-total-links"),
    statTotalClicks: document.getElementById("stat-total-clicks"),
    statActiveLinks: document.getElementById("stat-active-links"),
    urlsTableBody: document.getElementById("urls-table-body"),
    emptyState: document.getElementById("empty-state"),

    // Analytics
    analyticsBackBtn: document.getElementById("analytics-back-btn"),
    analyticsShortUrl: document.getElementById("analytics-short-url"),
    analyticsOriginalUrl: document.getElementById("analytics-original-url"),
    analyticsTotalClicks: document.getElementById("analytics-total-clicks"),
    analyticsCreatedDate: document.getElementById("analytics-created-date"),
    analyticsLastClick: document.getElementById("analytics-last-click"),
    chartContainer: document.getElementById("chart-container"),

    toastContainer: document.getElementById("toast-container")
  };

  // Helpers
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function getGreeting(name) {
    const hour = new Date().getHours();
    let timeGreeting = "Good evening";
    if (hour < 12) timeGreeting = "Good morning";
    else if (hour < 17) timeGreeting = "Good afternoon";
    return `${timeGreeting}, ${name} 👋`;
  }

  function extractUserName(email) {
    if (!email) return "User";
    const part = email.split("@")[0];
    return part.charAt(0).toUpperCase() + part.slice(1);
  }

  function formatDate(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function formatShortDate(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    if (state.token) {
      headers["Authorization"] = `Bearer ${state.token}`;
    }
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });

      if (res.status === 401) {
        logout();
        throw new Error("Session expired. Please log in again.");
      }

      if (res.status === 429) {
        const retryAfter = res.headers.get("Retry-After") || "a few";
        throw new Error(`Rate limit exceeded. Please wait ${retryAfter} seconds.`);
      }

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errMsg = (data && (data.detail || data.message)) || "Request failed";
        throw new Error(errMsg);
      }

      return data;
    } catch (err) {
      throw err;
    }
  }

  // Views Navigation
  function switchView(viewName) {
    el.authView.style.display = viewName === "auth" ? "flex" : "none";
    el.dashboardView.style.display = viewName === "dashboard" ? "block" : "none";
    el.analyticsView.style.display = viewName === "analytics" ? "block" : "none";

    if (viewName === "auth") {
      el.userNav.style.display = "none";
    } else {
      el.userNav.style.display = "flex";
    }
  }

  // Auth Functions
  function setAuthMode(mode) {
    state.authMode = mode;
    if (mode === "signup") {
      el.authSubtitle.textContent = "Create your account";
      el.authSubmitBtn.textContent = "Create Account";
      el.authSwitchText.textContent = "Already have an account?";
      el.authSwitchBtn.textContent = "Sign in";
    } else {
      el.authSubtitle.textContent = "Welcome back";
      el.authSubmitBtn.textContent = "Sign in";
      el.authSwitchText.textContent = "Don't have an account?";
      el.authSwitchBtn.textContent = "Create one";
    }
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    const email = el.authEmail.value.trim();
    const password = el.authPassword.value.trim();

    if (!email || !password) {
      showToast("Please fill in all fields", "error");
      return;
    }

    el.authSubmitBtn.disabled = true;
    el.authSubmitBtn.textContent = state.authMode === "signup" ? "Creating account..." : "Signing in...";

    try {
      const endpoint = state.authMode === "signup" ? "/auth/signup" : "/auth/login";
      const data = await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify({ email, password })
      });

      state.token = data.access_token;
      state.user = data.user;
      localStorage.setItem("shortx_token", data.access_token);

      showToast(state.authMode === "signup" ? "Account created successfully!" : "Signed in successfully!", "success");
      el.authForm.reset();
      initDashboard();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      el.authSubmitBtn.disabled = false;
      el.authSubmitBtn.textContent = state.authMode === "signup" ? "Create Account" : "Sign in";
    }
  }

  function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem("shortx_token");
    setAuthMode("login");
    switchView("auth");
    showToast("Signed out", "info");
  }

  // Dashboard Functions
  async function initDashboard() {
    if (!state.token) {
      setAuthMode("signup");
      switchView("auth");
      return;
    }

    try {
      // Fetch user profile if not cached
      if (!state.user) {
        state.user = await apiRequest("/auth/me");
      }

      const userName = extractUserName(state.user.email);
      el.dashboardGreeting.textContent = getGreeting(userName);
      el.navGreeting.textContent = userName;

      switchView("dashboard");
      await loadDashboardData();
    } catch (err) {
      logout();
    }
  }

  async function loadDashboardData() {
    try {
      const [stats, urls] = await Promise.all([
        apiRequest("/urls/stats"),
        apiRequest("/urls")
      ]);

      state.stats = stats;
      state.urls = urls;

      el.statTotalLinks.textContent = stats.total_links;
      el.statTotalClicks.textContent = stats.total_clicks;
      el.statActiveLinks.textContent = stats.active_links;

      renderUrlsTable(urls);
    } catch (err) {
      showToast("Error loading links: " + err.message, "error");
    }
  }

  function renderUrlsTable(urls) {
    el.urlsTableBody.innerHTML = "";

    if (!urls || urls.length === 0) {
      el.emptyState.style.display = "block";
      return;
    }

    el.emptyState.style.display = "none";

    urls.forEach(item => {
      const tr = document.createElement("tr");

      // Clean short url display without protocol
      const shortDisplay = item.short_url.replace(/^https?:\/\//, "");

      tr.innerHTML = `
        <td class="cell-original" title="${escapeHtml(item.original_url)}">
          ${escapeHtml(item.original_url)}
        </td>
        <td class="cell-short">
          <a href="${item.short_url}" target="_blank" rel="noopener noreferrer">${shortDisplay}</a>
        </td>
        <td class="cell-clicks">${item.click_count}</td>
        <td class="cell-date">${formatShortDate(item.created_at)}</td>
        <td style="text-align: right;">
          <div class="action-buttons" style="justify-content: flex-end;">
            <button class="btn-action btn-copy" data-short="${item.short_url}">Copy</button>
            <button class="btn-action btn-action-analytics" data-id="${item.id}">Analytics</button>
            <button class="btn-action btn-action-delete" data-id="${item.id}">Delete</button>
          </div>
        </td>
      `;

      el.urlsTableBody.appendChild(tr);
    });

    // Attach row events
    el.urlsTableBody.querySelectorAll(".btn-copy").forEach(btn => {
      btn.addEventListener("click", () => {
        copyToClipboard(btn.dataset.short);
        const originalText = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = originalText; }, 1500);
      });
    });

    el.urlsTableBody.querySelectorAll(".btn-action-analytics").forEach(btn => {
      btn.addEventListener("click", () => {
        openAnalytics(parseInt(btn.dataset.id, 10));
      });
    });

    el.urlsTableBody.querySelectorAll(".btn-action-delete").forEach(btn => {
      btn.addEventListener("click", () => {
        deleteUrl(parseInt(btn.dataset.id, 10));
      });
    });
  }

  async function handleShortenSubmit(e) {
    e.preventDefault();
    const url = el.urlInput.value.trim();
    if (!url) return;

    el.btnShorten.disabled = true;
    el.btnShorten.textContent = "Shortening...";

    try {
      const created = await apiRequest("/urls", {
        method: "POST",
        body: JSON.stringify({ original_url: url })
      });

      el.createdShortLink.textContent = created.short_url.replace(/^https?:\/\//, "");
      el.createdBanner.style.display = "flex";
      el.btnCopyCreated.onclick = () => {
        copyToClipboard(created.short_url);
        el.btnCopyCreated.textContent = "Copied!";
        setTimeout(() => { el.btnCopyCreated.textContent = "Copy"; }, 1500);
      };

      el.urlInput.value = "";
      showToast("URL shortened successfully!", "success");
      await loadDashboardData();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      el.btnShorten.disabled = false;
      el.btnShorten.textContent = "Shorten";
    }
  }

  async function deleteUrl(id) {
    if (!confirm("Are you sure you want to delete this short link?")) return;

    try {
      await apiRequest(`/urls/${id}`, { method: "DELETE" });
      showToast("Short link deleted", "info");
      await loadDashboardData();
    } catch (err) {
      showToast("Failed to delete link: " + err.message, "error");
    }
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
      showToast("Copied to clipboard!", "success");
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
      showToast("Copied to clipboard!", "success");
    }
  }

  // Analytics Functions
  async function openAnalytics(urlId) {
    try {
      const data = await apiRequest(`/urls/${urlId}/analytics`);
      state.activeAnalyticsUrl = data;

      el.analyticsShortUrl.textContent = data.short_url.replace(/^https?:\/\//, "");
      el.analyticsOriginalUrl.textContent = data.original_url;
      el.analyticsTotalClicks.textContent = data.total_clicks;
      el.analyticsCreatedDate.textContent = formatDate(data.created_at);
      el.analyticsLastClick.textContent = formatDate(data.last_click_at);

      renderSvgChart(data.clicks_timeline);
      switchView("analytics");
    } catch (err) {
      showToast("Failed to load analytics: " + err.message, "error");
    }
  }

  function renderSvgChart(timeline) {
    if (!timeline || timeline.length === 0) {
      el.chartContainer.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 3rem;">No click activity recorded yet.</div>';
      return;
    }

    const width = 800;
    const height = 200;
    const padding = { top: 25, right: 30, bottom: 35, left: 40 };

    const maxClicks = Math.max(...timeline.map(t => t.clicks), 5);

    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const points = timeline.map((item, index) => {
      const x = padding.left + (index / (timeline.length - 1)) * chartW;
      const y = padding.top + chartH - (item.clicks / maxClicks) * chartH;
      return { x, y, ...item };
    });

    // Smooth Bezier Curve Path
    let pathD = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cpX = (p0.x + p1.x) / 2;
      pathD += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
    }

    // Area path for gradient fill
    const areaD = `${pathD} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

    // Horizontal grid lines
    let gridLinesSvg = "";
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      const y = padding.top + (chartH / steps) * i;
      const val = Math.round(maxClicks - (maxClicks / steps) * i);
      gridLinesSvg += `
        <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(255, 255, 255, 0.06)" stroke-dasharray="4" />
        <text x="${padding.left - 10}" y="${y + 4}" fill="#64748b" font-size="11" text-anchor="end">${val}</text>
      `;
    }

    // Labels & Data Dots
    let labelsSvg = "";
    let dotsSvg = "";
    points.forEach(p => {
      labelsSvg += `
        <text x="${p.x}" y="${height - 10}" fill="#94a3b8" font-size="11" text-anchor="middle">${p.date}</text>
      `;
      dotsSvg += `
        <circle cx="${p.x}" cy="${p.y}" r="4.5" fill="#6366f1" stroke="#0f172a" stroke-width="2" />
        <title>${p.date}: ${p.clicks} clicks</title>
      `;
    });

    el.chartContainer.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: 100%; overflow: visible;">
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#6366f1" stop-opacity="0.35" />
            <stop offset="100%" stop-color="#6366f1" stop-opacity="0.0" />
          </linearGradient>
        </defs>
        ${gridLinesSvg}
        <path d="${areaD}" fill="url(#chartGradient)" />
        <path d="${pathD}" fill="none" stroke="#6366f1" stroke-width="3" stroke-linecap="round" />
        ${dotsSvg}
        ${labelsSvg}
      </svg>
    `;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Event Listeners
  el.authSwitchBtn.addEventListener("click", () => {
    setAuthMode(state.authMode === "signup" ? "login" : "signup");
  });

  el.authForm.addEventListener("submit", handleAuthSubmit);
  el.logoutBtn.addEventListener("click", logout);
  el.brandLink.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.token) {
      switchView("dashboard");
    } else {
      switchView("auth");
    }
  });

  el.shortenForm.addEventListener("submit", handleShortenSubmit);
  el.analyticsBackBtn.addEventListener("click", () => switchView("dashboard"));

  // App Initialization
  initDashboard();
})();
