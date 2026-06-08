// ── State ─────────────────────────────────────────────────────────────────────
let allJobs = [];
let currentFilter   = "all";
let currentPlatform = "all";
let currentTab = "all";

const TAB_TITLES = {
  all: "Дашборд",
  review: "Ожидают решения",
  approved: "Подходящие задания",
  profile: "Мой профиль",
};

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkProfile();
  loadJobs();
  setupNav();

  document.getElementById("menu-btn").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
});

function checkProfile() {
  const local = localStorage.getItem("fh_profile");
  if (!local) {
    // No profile yet — send to onboarding
    fetch("/api/get-profile")
      .then(r => r.json())
      .then(d => { if (!d.exists) window.location.href = "onboarding.html"; })
      .catch(() => {}); // If API down, stay on dashboard
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
function setupNav() {
  document.querySelectorAll(".nav-item[data-tab]").forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      switchTab(el.dataset.tab);
      document.getElementById("sidebar").classList.remove("open");
    });
  });

  document.querySelectorAll(".card-link[data-tab]").forEach(el => {
    el.addEventListener("click", e => { e.preventDefault(); switchTab(el.dataset.tab); });
  });
}

function switchTab(tab) {
  currentTab = tab;

  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item[data-tab]").forEach(n => n.classList.remove("active"));

  document.getElementById("tab-" + tab)?.classList.add("active");
  document.querySelector(`[data-tab="${tab}"]`)?.classList.add("active");
  document.getElementById("topbar-title").textContent = TAB_TITLES[tab] || tab;

  if (tab === "review")   renderList("review-list", filtered("review"));
  if (tab === "approved") renderList("approved-list", filtered("approved"));
  if (tab === "profile")  renderProfile();
}

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadJobs(silent = false) {
  try {
    const res = await fetch("/api/get-jobs");
    const data = await res.json();
    allJobs = data.jobs || [];
    updateStats(data.stats || {});
    renderCurrentView();
    setStatus("online", "Подключено");
    if (!silent) {
      document.getElementById("last-update").textContent =
        "Обновлено в " + new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    }
  } catch {
    // API unavailable — use demo data
    allJobs = getDemoJobs();
    updateStats(calcStats(allJobs));
    renderCurrentView();
    setStatus("warn", "Демо режим");
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function calcStats(jobs) {
  const today = new Date().toDateString();
  return {
    total: jobs.length,
    approved: jobs.filter(j => j.status === "approved").length,
    review: jobs.filter(j => j.status === "review").length,
    rejected: jobs.filter(j => j.status === "rejected").length,
    today: jobs.filter(j => new Date(j.created_at).toDateString() === today).length,
  };
}

function updateStats(stats) {
  const s = Object.keys(stats).length ? stats : calcStats(allJobs);
  setText("stat-today",    s.today    ?? "—");
  setText("stat-approved", s.approved ?? "—");
  setText("stat-review",   s.review   ?? "—");
  setText("stat-rejected", s.rejected ?? "—");

  const r = allJobs.filter(j => j.status === "review").length;
  const a = allJobs.filter(j => j.status === "approved").length;
  document.getElementById("badge-review").textContent = r;
  document.getElementById("badge-approved").textContent = a;
  document.getElementById("badge-review").style.display = r ? "" : "none";
  document.getElementById("badge-approved").style.display = a ? "" : "none";
}

// ── Filtering ─────────────────────────────────────────────────────────────────
function filtered(status) {
  let jobs = status === "all" ? allJobs : allJobs.filter(j => j.status === status);
  if (currentPlatform !== "all") jobs = jobs.filter(j => j.platform === currentPlatform);
  return jobs;
}

function setFilter(el, filter) {
  currentFilter = filter;
  document.querySelectorAll(".filter-btn:not(.plt)").forEach(b => b.classList.remove("active"));
  el.classList.add("active");
  renderList("jobs-list", filtered(filter));
}

function setPlatform(el, platform) {
  currentPlatform = platform;
  document.querySelectorAll(".filter-btn.plt").forEach(b => b.classList.remove("active"));
  el.classList.add("active");
  renderList("jobs-list", filtered(currentFilter));
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderCurrentView() {
  renderList("jobs-list", filtered(currentFilter));
  updateStats({});
  if (currentTab === "review")   renderList("review-list", filtered("review"));
  if (currentTab === "approved") renderList("approved-list", filtered("approved"));
}

function renderList(containerId, jobs) {
  const el = document.getElementById(containerId);
  if (!el) return;

  if (!jobs.length) {
    el.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-title">Заданий нет</div>
        <div class="empty-hint">Нажми «Сканировать» чтобы загрузить задания</div>
      </div>`;
    return;
  }

  el.innerHTML = jobs.map(job => jobCard(job)).join("");
}

function jobCard(job) {
  const statusClass = { approved: "status-approved", review: "status-review", rejected: "status-rejected", pending: "status-pending" }[job.status] || "";
  const statusLabel = { approved: "✅ Подходит", review: "⚡ На проверку", rejected: "❌ Отклонено", pending: "⏳ Анализ..." }[job.status] || job.status;
  const scoreBar = job.score ? `<div class="score-bar"><div class="score-fill" style="width:${job.score * 10}%;background:${scoreColor(job.score)}"></div></div>` : "";

  const price = job.price ? `<span class="job-price">💰 $${job.price}</span>` : `<span class="job-price muted">цена не указана</span>`;
  const plt = PLATFORMS[job.platform] || { icon: "🔘", label: job.platform };

  const actions = [];
  if (job.url && job.url !== "#") {
    actions.push(`<a href="${esc(job.url)}" target="_blank" rel="noopener" class="job-btn btn-open">🔗 Открыть</a>`);
  }
  if (job.status === "review") {
    actions.push(`<button class="job-btn btn-approve" onclick="updateJob('${esc(job.id)}','save')">✅ Хорошо</button>`);
    actions.push(`<button class="job-btn btn-skip" onclick="updateJob('${esc(job.id)}','skip')">❌ Пропустить</button>`);
  }
  if (job.status === "approved") {
    actions.push(`<button class="job-btn btn-skip" onclick="updateJob('${esc(job.id)}','skip')">❌ Пропустить</button>`);
  }
  if (job.status === "rejected") {
    actions.push(`<button class="job-btn btn-restore" onclick="updateJob('${esc(job.id)}','restore')">↩️ Восстановить</button>`);
  }

  return `
    <article class="job-card ${statusClass}" id="card-${esc(job.id)}">
      <div class="job-card-top">
        <div class="job-meta-row">
          <span class="job-platform">${plt.icon} ${plt.label}</span>
          <span class="job-time">${timeAgo(job.created_at)}</span>
          <span class="job-status-pill ${statusClass}">${statusLabel}</span>
        </div>
        <h3 class="job-title">${esc(job.title)}</h3>
        <div class="job-price-row">
          ${price}
          ${job.score ? `<span class="job-score" style="color:${scoreColor(job.score)}">★ ${job.score}/10</span>` : ""}
        </div>
      </div>

      ${job.reason ? `
        <div class="job-reason">
          <span class="reason-label">ИИ:</span> ${esc(job.reason)}
          ${scoreBar}
        </div>` : ""}

      ${job.description ? `<p class="job-desc">${esc(job.description.slice(0, 200))}${job.description.length > 200 ? "..." : ""}</p>` : ""}

      ${actions.length ? `<div class="job-actions">${actions.join("")}</div>` : ""}
    </article>`;
}

function scoreColor(score) {
  if (score >= 8) return "#10b981";
  if (score >= 5) return "#f59e0b";
  return "#ef4444";
}

// Platform icons & labels
const PLATFORMS = {
  "fl.ru":         { icon: "🔵", label: "FL.ru" },
  "freelancehunt": { icon: "🟡", label: "Freelancehunt" },
};

// ── Actions ───────────────────────────────────────────────────────────────────
async function updateJob(jobId, action) {
  // Optimistic update
  const job = allJobs.find(j => j.id === jobId);
  if (job) {
    if (action === "skip")    job.status = "rejected";
    if (action === "save")    job.status = "approved";
    if (action === "restore") job.status = "review";
  }
  renderCurrentView();

  try {
    await fetch("/api/update-job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, action }),
    });
  } catch {
    // Silent fail — local state is already updated
  }

  const msgs = { skip: "Задание пропущено", save: "Задание сохранено ✅", restore: "Задание восстановлено" };
  showToast(msgs[action] || "Готово", action === "save" ? "success" : "info");
}

async function triggerScan() {
  const btn = document.getElementById("scan-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Сканирую...';
  setStatus("warn", "Сканирование...");

  try {
    const res = await fetch("/api/parse-jobs", { method: "POST" });
    const d = await res.json();
    showToast(`Найдено новых: ${d.new_jobs ?? 0}`, "success");

    // Trigger AI analysis right after
    await fetch("/api/analyze-jobs", { method: "POST" });
    await loadJobs(true);
    showToast("Анализ завершён", "success");
    setStatus("online", "Подключено");
  } catch {
    showToast("API недоступен — демо режим", "warn");
    setStatus("warn", "Демо режим");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🔄 Сканировать";
  }
}

// ── Profile tab ───────────────────────────────────────────────────────────────
async function renderProfile() {
  let profile = null;

  // Try local first, then API
  const local = localStorage.getItem("fh_profile");
  if (local) {
    try { profile = JSON.parse(local); } catch {}
  }

  if (!profile) {
    try {
      const res = await fetch("/api/get-profile");
      const d = await res.json();
      profile = d.profile;
    } catch {}
  }

  const el = document.getElementById("profile-display");
  if (!el) return;

  if (!profile) {
    el.innerHTML = `<p>Профиль не найден. <a href="onboarding.html">Пройти настройку →</a></p>`;
    return;
  }

  const EXP = { junior: "🌱 Начинающий", middle: "🔥 Средний", senior: "💎 Опытный" };
  const DIR = { dev: "💻 Разработка", design: "🎨 Дизайн", copy: "✍️ Копирайтинг", other: "🔧 Другое" };

  el.innerHTML = `
    <div class="profile-row"><span class="profile-key">Направление</span><span class="profile-val">${DIR[profile.direction] || profile.direction}</span></div>
    <div class="profile-row"><span class="profile-key">Опыт</span><span class="profile-val">${EXP[profile.experience] || profile.experience}</span></div>
    <div class="profile-row"><span class="profile-key">Мин. цена</span><span class="profile-val">${profile.min_price ? "$" + profile.min_price : "не задана"}</span></div>
    <div class="profile-row">
      <span class="profile-key">Навыки</span>
      <span class="profile-val skills-wrap">${(profile.skills || []).map(s => `<span class="ob-tag">${esc(s)}</span>`).join("")}</span>
    </div>
    <div class="profile-row">
      <span class="profile-key">Исключения</span>
      <span class="profile-val">${(profile.excluded || []).join(", ") || "нет"}</span>
    </div>`;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const icons = { success: "✅", warn: "⚠️", error: "❌", info: "ℹ️" };
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span>${icons[type] || ""}</span><span>${esc(msg)}</span>`;
  document.getElementById("toast-box").appendChild(el);
  setTimeout(() => { el.classList.add("hide"); setTimeout(() => el.remove(), 300); }, 3000);
}

// ── Status dot ────────────────────────────────────────────────────────────────
function setStatus(type, text) {
  const dot = document.getElementById("status-dot");
  dot.className = "status-dot " + type;
  document.getElementById("status-text").textContent = text;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso);
  const m = Math.floor(diff / 60000);
  if (m < 1)  return "только что";
  if (m < 60) return `${m} мин назад`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ч назад`;
  return `${Math.floor(h / 24)} д назад`;
}

// ── Demo data (when API is unavailable) ───────────────────────────────────────
function getDemoJobs() {
  const now = new Date();
  const ago = m => new Date(now - m * 60000).toISOString();
  return [
    { id:"d1", platform:"fl.ru",          title:"Разработка Telegram-бота для доставки еды",   description:"Нужен бот с функцией заказа, оплаты через ЮКасса и уведомлениями.", price:850,  url:"#", status:"approved",  score:9,  reason:"Отлично подходит — Python + Telegram Bot в твоём стеке.", created_at: ago(8) },
    { id:"d2", platform:"freelancehunt", title:"FastAPI бэкенд для мобильного приложения",    description:"REST API, PostgreSQL, авторизация JWT, деплой на VPS.", price:1200, url:"#", status:"approved",  score:10, reason:"Идеальное совпадение навыков и отличный бюджет.", created_at: ago(22) },
    { id:"d3", platform:"fl.ru",          title:"Парсер товаров с Wildberries",                description:"Собрать цены, остатки, рейтинг по списку SKU в реальном времени.", price:300, url:"#", status:"review",   score:7,  reason:"Парсинг — твоя тема, но цена немного ниже обычного.", created_at: ago(35) },
    { id:"d4", platform:"freelancehunt", title:"Интернет-магазин на React + Node.js",         description:"Каталог, корзина, личный кабинет, интеграция с 1С.", price:400, url:"#", status:"review",   score:6,  reason:"Подходит по React, но есть интеграция с 1С — уточни детали.", created_at: ago(55) },
    { id:"d5", platform:"freelancehunt", title:"Data pipeline на Python + Airflow",            description:"ETL процесс для аналитики, PostgreSQL, scheduled tasks.", price:900, url:"#", status:"approved",  score:8,  reason:"Python + базы данных — прямое попадание в стек.", created_at: ago(70) },
    { id:"d6", platform:"fl.ru",          title:"Сайт-визитка на WordPress",                   description:"Простой корпоративный сайт, 5-7 страниц.", price:80, url:"#", status:"rejected", score:2,  reason:"WordPress в списке исключений + цена ниже минимума.", created_at: ago(90) },
    { id:"d7", platform:"fl.ru",          title:"Скрипт автоматизации в Excel VBA",            description:"Макрос для формирования отчётов из нескольких таблиц.", price:120, url:"#", status:"rejected", score:3,  reason:"Не ваша специализация, цена ниже минимума.", created_at: ago(120) },
    { id:"d8", platform:"freelancehunt", title:"Бот для мониторинга цен на маркетплейсах",    description:"Парсинг Wildberries + Ozon, уведомления в Telegram при изменении цены.", price:500, url:"#", status:"approved",  score:9,  reason:"Парсинг + Telegram Bot — идеально под твои навыки.", created_at: ago(140) },
  ];
}
