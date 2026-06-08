// ── State ─────────────────────────────────────────────────────────────────────
let allJobs = [];
let currentFilter   = "all";
let currentPlatform = "all";
let currentTab      = "all";

const TAB_TITLES = {
  all:      "Дашборд",
  review:   "Ожидают решения",
  approved: "Подходящие задания",
  profile:  "Мой профиль",
};

// Platform icons & labels
const PLATFORMS = {
  "fl.ru":         { icon: "🔵", label: "FL.ru",         color: "#3b82f6" },
  "freelancehunt": { icon: "🟡", label: "Freelancehunt", color: "#f59e0b" },
};

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkProfile();
  loadJobs();
  setupNav();

  document.getElementById("menu-btn").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });

  // Close sidebar on overlay click (mobile)
  document.addEventListener("click", e => {
    const sb = document.getElementById("sidebar");
    if (sb.classList.contains("open") && !sb.contains(e.target) && e.target.id !== "menu-btn") {
      sb.classList.remove("open");
    }
  });
});

function checkProfile() {
  const local = localStorage.getItem("fh_profile");
  if (!local) {
    fetch("/api/get-profile")
      .then(r => r.json())
      .then(d => { if (!d.exists) window.location.href = "onboarding.html"; })
      .catch(() => {});
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
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item[data-tab]").forEach(n => n.classList.remove("active"));
  document.getElementById("tab-" + tab)?.classList.add("active");
  document.querySelector(`[data-tab="${tab}"]`)?.classList.add("active");
  document.getElementById("topbar-title").textContent = TAB_TITLES[tab] || tab;

  if (tab === "review")   renderList("review-list",   filtered("review"));
  if (tab === "approved") renderList("approved-list",  filtered("approved"));
  if (tab === "profile")  renderProfile();
}

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadJobs(silent = false) {
  try {
    const res  = await fetch("/api/get-jobs");
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
    allJobs = getDemoJobs();
    updateStats(calcStats(allJobs));
    renderCurrentView();
    setStatus("warn", "Демо режим");
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function calcStats(jobs) {
  const today = new Date().toISOString().slice(0, 10);
  return {
    total:    jobs.length,
    approved: jobs.filter(j => j.status === "approved").length,
    review:   jobs.filter(j => j.status === "review").length,
    rejected: jobs.filter(j => j.status === "rejected").length,
    pending:  jobs.filter(j => j.status === "pending").length,
    today:    jobs.filter(j => (j.created_at || "").startsWith(today)).length,
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
  const reviewBadge   = document.getElementById("badge-review");
  const approvedBadge = document.getElementById("badge-approved");
  if (reviewBadge)   { reviewBadge.textContent   = r; reviewBadge.style.display   = r ? "" : "none"; }
  if (approvedBadge) { approvedBadge.textContent = a; approvedBadge.style.display = a ? "" : "none"; }
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
  if (currentTab === "review")   renderList("review-list",  filtered("review"));
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
  const STATUS = {
    approved: { cls: "status-approved", label: "✅ Подходит" },
    review:   { cls: "status-review",   label: "⚡ Проверить" },
    rejected: { cls: "status-rejected", label: "❌ Отклонено" },
    pending:  { cls: "status-pending",  label: "⏳ Анализ..." },
  };
  const st  = STATUS[job.status] || STATUS.pending;
  const plt = PLATFORMS[job.platform] || { icon: "🔘", label: job.platform || "—", color: "#666" };

  const priceHtml = job.price
    ? `<span class="job-price">💰 $${job.price}</span>`
    : `<span class="job-price muted">цена не указана</span>`;

  // Score ring
  const scoreHtml = job.score ? `
    <div class="score-ring" title="Оценка ИИ: ${job.score}/10">
      <svg viewBox="0 0 36 36" class="score-svg">
        <circle class="score-bg"   cx="18" cy="18" r="15" />
        <circle class="score-fill" cx="18" cy="18" r="15"
          stroke="${scoreColor(job.score)}"
          stroke-dasharray="${job.score * 9.42} 94.2" />
      </svg>
      <span class="score-num" style="color:${scoreColor(job.score)}">${job.score}</span>
    </div>` : "";

  const actions = [];
  if (job.url && job.url !== "#")
    actions.push(`<a href="${esc(job.url)}" target="_blank" rel="noopener" class="job-btn btn-open">🔗 Открыть</a>`);
  if (job.status === "review") {
    actions.push(`<button class="job-btn btn-approve" onclick="updateJob('${esc(job.id)}','save')">✅ Сохранить</button>`);
    actions.push(`<button class="job-btn btn-skip"    onclick="updateJob('${esc(job.id)}','skip')">❌ Пропустить</button>`);
  }
  if (job.status === "approved")
    actions.push(`<button class="job-btn btn-skip" onclick="updateJob('${esc(job.id)}','skip')">❌ Пропустить</button>`);
  if (job.status === "rejected")
    actions.push(`<button class="job-btn btn-restore" onclick="updateJob('${esc(job.id)}','restore')">↩️ Восстановить</button>`);

  return `
    <article class="job-card ${st.cls}" id="card-${esc(job.id)}">
      <div class="job-card-inner">
        <div class="job-card-body">
          <div class="job-meta-row">
            <span class="job-platform-badge" style="color:${plt.color};border-color:${plt.color}44;background:${plt.color}18">${plt.icon} ${plt.label}</span>
            <span class="job-time">${timeAgo(job.created_at)}</span>
            <span class="job-status-pill ${st.cls}">${st.label}</span>
          </div>
          <h3 class="job-title">${esc(job.title)}</h3>
          <div class="job-price-row">
            ${priceHtml}
          </div>
          ${job.reason ? `
            <div class="job-reason">
              <span class="reason-label">🤖 ИИ:</span> ${esc(job.reason)}
            </div>` : ""}
          ${job.description ? `<p class="job-desc">${esc(job.description.slice(0, 220))}${job.description.length > 220 ? "…" : ""}</p>` : ""}
          ${actions.length ? `<div class="job-actions">${actions.join("")}</div>` : ""}
        </div>
        ${scoreHtml ? `<div class="job-card-score">${scoreHtml}</div>` : ""}
      </div>
    </article>`;
}

function scoreColor(s) {
  if (s >= 8) return "#10b981";
  if (s >= 5) return "#f59e0b";
  return "#ef4444";
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function updateJob(jobId, action) {
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
  } catch { /* silent fail */ }

  const msgs = { skip: "Пропущено", save: "Сохранено ✅", restore: "Восстановлено" };
  showToast(msgs[action] || "Готово", action === "save" ? "success" : "info");
}

// ── Scan: parse → analyze (batched loop) ─────────────────────────────────────
async function triggerScan() {
  const btn = document.getElementById("scan-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Парсинг...';
  setStatus("warn", "Сканирование...");

  try {
    // Step 1: parse
    const parseRes = await fetch("/api/parse-jobs", { method: "POST" });
    const parseData = await parseRes.json();
    const newJobs = parseData.new_jobs ?? 0;
    showToast(`Найдено новых: ${newJobs}`, newJobs > 0 ? "success" : "info");

    if (newJobs === 0) {
      await loadJobs(true);
      setStatus("online", "Подключено");
      return;
    }

    // Step 2: analyze in batches (handles Vercel 10s timeout)
    btn.innerHTML = '<span class="spinner"></span> Анализ ИИ...';
    let totalAnalyzed = 0;
    let rounds = 0;
    const MAX_ROUNDS = 20; // safety cap

    while (rounds < MAX_ROUNDS) {
      const aRes  = await fetch("/api/analyze-jobs", { method: "POST" });
      const aData = await aRes.json();
      totalAnalyzed += aData.analyzed || 0;
      rounds++;

      // Refresh UI after each batch
      await loadJobs(true);

      if (!aData.has_more) break;
      // Small pause between batches so UI can breathe
      await sleep(500);
    }

    showToast(`Анализ завершён: ${totalAnalyzed} заданий оценено`, "success");
    setStatus("online", "Подключено");
  } catch (e) {
    console.error(e);
    showToast("Ошибка при сканировании", "error");
    setStatus("error", "Ошибка");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🔄 Сканировать";
    document.getElementById("last-update").textContent =
      "Обновлено в " + new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ── Profile tab ───────────────────────────────────────────────────────────────
async function renderProfile() {
  let profile = null;
  const local = localStorage.getItem("fh_profile");
  if (local) { try { profile = JSON.parse(local); } catch {} }

  if (!profile) {
    try {
      const res  = await fetch("/api/get-profile");
      const d    = await res.json();
      profile = d.profile;
    } catch {}
  }

  const el = document.getElementById("profile-display");
  if (!el) return;

  if (!profile) {
    el.innerHTML = `<p style="color:var(--muted)">Профиль не найден. <a href="onboarding.html" style="color:var(--accent)">Пройти настройку →</a></p>`;
    return;
  }

  const EXP = { junior: "🌱 Начинающий", middle: "🔥 Средний", senior: "💎 Опытный" };
  const DIR = { dev: "💻 Разработка",   design: "🎨 Дизайн",    copy: "✍️ Копирайтинг", other: "🔧 Другое" };

  el.innerHTML = `
    <div class="profile-row"><span class="profile-key">Направление</span><span class="profile-val">${DIR[profile.direction] || profile.direction}</span></div>
    <div class="profile-row"><span class="profile-key">Опыт</span><span class="profile-val">${EXP[profile.experience] || profile.experience}</span></div>
    <div class="profile-row"><span class="profile-key">Мин. цена</span><span class="profile-val">${profile.min_price ? "<strong>$" + profile.min_price + "</strong>" : "не задана"}</span></div>
    <div class="profile-row">
      <span class="profile-key">Навыки</span>
      <span class="profile-val skills-wrap">${(profile.skills || []).map(s => `<span class="ob-tag">${esc(s)}</span>`).join("")}</span>
    </div>
    <div class="profile-row">
      <span class="profile-key">Исключения</span>
      <span class="profile-val">${(profile.excluded || []).map(s => `<span class="excl-tag">${esc(s)}</span>`).join("") || '<span style="color:var(--muted)">нет</span>'}</span>
    </div>`;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const icons = { success: "✅", warn: "⚠️", error: "❌", info: "ℹ️" };
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span>${icons[type] || ""}</span><span>${esc(msg)}</span>`;
  document.getElementById("toast-box").appendChild(el);
  setTimeout(() => { el.classList.add("hide"); setTimeout(() => el.remove(), 350); }, 3500);
}

// ── Status dot ────────────────────────────────────────────────────────────────
function setStatus(type, text) {
  document.getElementById("status-dot").className = "status-dot " + type;
  document.getElementById("status-text").textContent = text;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val; }
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

// ── Demo data ─────────────────────────────────────────────────────────────────
function getDemoJobs() {
  const now = new Date();
  const ago = m => new Date(now - m * 60000).toISOString();
  return [
    { id:"d1", platform:"fl.ru",          title:"Разработка Telegram-бота для доставки еды",        description:"Нужен бот с функцией заказа, оплаты через ЮКасса и уведомлениями для курьеров.", price:850,  url:"#", status:"approved",  score:9,  reason:"Отлично подходит — Python + Telegram Bot прямо в твоём стеке. Бюджет выше минимума.", created_at: ago(8) },
    { id:"d2", platform:"freelancehunt",  title:"FastAPI бэкенд для мобильного приложения",         description:"REST API, PostgreSQL, авторизация JWT, деплой на VPS. Срочно.", price:1200, url:"#", status:"approved",  score:10, reason:"Идеальное совпадение по всем навыкам: FastAPI, PostgreSQL, JWT. Бюджет отличный.", created_at: ago(22) },
    { id:"d3", platform:"fl.ru",          title:"Парсер товаров с Wildberries на Python",            description:"Собрать цены, остатки и рейтинг по списку SKU, сохранять в Excel каждый час.", price:300,  url:"#", status:"review",   score:6,  reason:"Парсинг на Python — твоя тема. Цена чуть ниже обычного, стоит уточнить детали.", created_at: ago(35) },
    { id:"d4", platform:"freelancehunt",  title:"Интернет-магазин на React + Node.js + PostgreSQL",  description:"Каталог товаров, корзина, личный кабинет, интеграция с 1С.", price:400,  url:"#", status:"review",   score:7,  reason:"Хорошее совпадение по React и Node. Интеграция с 1С — уточни объём работы.", created_at: ago(55) },
    { id:"d5", platform:"freelancehunt",  title:"Data pipeline на Python + Apache Airflow",          description:"ETL-процесс для BI-аналитики, PostgreSQL, scheduled tasks, Docker.", price:900,  url:"#", status:"approved",  score:8,  reason:"Python + базы данных — прямое попадание в стек. Airflow — плюс к скиллам.", created_at: ago(70) },
    { id:"d6", platform:"fl.ru",          title:"Сайт-визитка на WordPress для стоматологии",        description:"Простой корпоративный сайт, 5–7 страниц, тема Elementor.", price:80,   url:"#", status:"rejected", score:2,  reason:"WordPress в списке исключений. Цена $80 — ниже минимума в три раза.", created_at: ago(90) },
    { id:"d7", platform:"fl.ru",          title:"Бот для мониторинга цен на маркетплейсах",          description:"Парсинг Wildberries + Ozon, уведомления в Telegram при изменении цены.", price:500,  url:"#", status:"approved",  score:9,  reason:"Парсинг + Telegram Bot — идеально. Бюджет в норме.", created_at: ago(140) },
  ];
}
