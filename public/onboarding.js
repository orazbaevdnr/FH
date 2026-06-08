// ── Auth guard ────────────────────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem("fh_token") || "";
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + getToken(),
  };
}

// Redirect to login if no token
(function authGuard() {
  if (!getToken()) {
    window.location.href = "/login.html";
  }
})();

// ── State ────────────────────────────────────────────────────────────────────
const profile = {
  direction: "",
  skills:    [],
  experience: "",
  min_price: 200,
  excluded:  [],
};

let currentStep = 1;
const TOTAL_STEPS = 5;
let skillsData = {};

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  updateProgress();
  fetchSkills();
});

async function fetchSkills() {
  try {
    const res = await fetch("/data/skills.json");
    skillsData = await res.json();
  } catch {
    skillsData = {
      dev:    { skills: ["Python","JavaScript","React","TypeScript","Django","FastAPI","Node.js","Docker","Telegram Bot","Парсинг","PostgreSQL","MongoDB","REST API","Vue.js","Redis","GraphQL"] },
      design: { skills: ["Figma","Photoshop","Illustrator","UI/UX","Веб-дизайн","Логотипы","Брендинг","Adobe XD","Анимация","After Effects","3D","Canva"] },
      copy:   { skills: ["SEO-тексты","Статьи","Переводы","Лендинги","Email-рассылки","SMM-контент","Редактура","Сценарии","Описания товаров"] },
      other:  { skills: ["Excel","1C","Битрикс24","Тестирование","Data Science","Аналитика","Excel VBA","Управление проектами","Таргет","Яндекс.Директ"] },
    };
  }
}

// ── Progress ──────────────────────────────────────────────────────────────────
function updateProgress() {
  const pct = ((currentStep - 1) / (TOTAL_STEPS - 1)) * 100;
  document.getElementById("progress-fill").style.width = pct + "%";
  document.getElementById("step-num").textContent = currentStep;

  document.getElementById("btn-back").style.visibility =
    currentStep === 1 ? "hidden" : "visible";

  const nextBtn = document.getElementById("btn-next");
  if (currentStep === TOTAL_STEPS) {
    nextBtn.textContent = "💾 Сохранить и начать";
    nextBtn.classList.add("ob-btn-save");
  } else {
    nextBtn.textContent = "Далее →";
    nextBtn.classList.remove("ob-btn-save");
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
function nextStep() {
  if (!validateStep(currentStep)) return;
  if (currentStep === TOTAL_STEPS) { saveProfile(); return; }
  goToStep(currentStep + 1);
}

function prevStep() {
  if (currentStep > 1) goToStep(currentStep - 1);
}

function goToStep(n) {
  document.getElementById(`step-${currentStep}`).classList.remove("active");
  currentStep = n;
  document.getElementById(`step-${currentStep}`).classList.add("active");
  updateProgress();
  if (n === 2 && profile.direction) renderSkillChips();
  if (n === 5) renderSummary();
}

// ── Validation ────────────────────────────────────────────────────────────────
function validateStep(step) {
  hideError(step);
  if (step === 1 && !profile.direction)  { showError(1, "Выбери направление"); return false; }
  if (step === 2 && !profile.skills.length) { showError(2, "Выбери хотя бы один навык"); return false; }
  if (step === 3 && !profile.experience) { showError(3, "Выбери уровень опыта"); return false; }
  if (step === 4) {
    const price = parseInt(document.getElementById("min-price").value, 10);
    profile.min_price = isNaN(price) ? 0 : price;
    const excRaw = document.getElementById("excluded").value;
    profile.excluded = excRaw.split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
  }
  return true;
}

function showError(step, msg) {
  const el = document.getElementById(`err-${step}`);
  if (el) { el.textContent = msg; el.classList.remove("hidden"); }
}
function hideError(step) {
  const el = document.getElementById(`err-${step}`);
  if (el) el.classList.add("hidden");
}

// ── Step 1: Direction ─────────────────────────────────────────────────────────
function selectDir(el) {
  document.querySelectorAll(".dir-card").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
  profile.direction = el.dataset.dir;
  profile.skills = [];
}

// ── Step 2: Skills ────────────────────────────────────────────────────────────
function renderSkillChips() {
  const data = skillsData[profile.direction] || { skills: [] };
  const container = document.getElementById("skill-chips");

  container.innerHTML = data.skills.map(skill => {
    const active = profile.skills.includes(skill) ? "active" : "";
    return `<button class="skill-chip ${active}" onclick="toggleSkill(this,'${escAttr(skill)}')">${esc(skill)}</button>`;
  }).join("");

  updateSelectedDisplay();
}

function toggleSkill(el, skill) {
  const idx = profile.skills.indexOf(skill);
  if (idx === -1) { profile.skills.push(skill); el.classList.add("active"); }
  else            { profile.skills.splice(idx, 1); el.classList.remove("active"); }
  updateSelectedDisplay();
}

function addCustomSkill() {
  const input = document.getElementById("custom-skill");
  const val = input.value.trim();
  if (!val || profile.skills.includes(val)) { input.value = ""; return; }
  profile.skills.push(val);
  const chip = document.createElement("button");
  chip.className = "skill-chip active";
  chip.textContent = val;
  chip.onclick = () => toggleSkill(chip, val);
  document.getElementById("skill-chips").appendChild(chip);
  input.value = "";
  updateSelectedDisplay();
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("custom-skill")?.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); addCustomSkill(); }
  });
});

function updateSelectedDisplay() {
  document.getElementById("selected-count").textContent = profile.skills.length;
  document.getElementById("selected-tags").innerHTML = profile.skills
    .map(s => `<span class="ob-tag">${esc(s)}</span>`).join("");
}

// ── Step 3: Experience ────────────────────────────────────────────────────────
function selectExp(el) {
  document.querySelectorAll(".exp-card").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
  profile.experience = el.dataset.exp;
}

// ── Step 5: Summary ───────────────────────────────────────────────────────────
const EXP_LABELS = { junior: "🌱 Начинающий (до 1 года)", middle: "🔥 Средний (1–3 года)", senior: "💎 Опытный (3+ года)" };
const DIR_LABELS = { dev: "💻 Разработка", design: "🎨 Дизайн", copy: "✍️ Копирайтинг", other: "🔧 Другое" };

function renderSummary() {
  document.getElementById("sum-direction").textContent = DIR_LABELS[profile.direction] || profile.direction;
  document.getElementById("sum-skills").textContent    = profile.skills.join(", ") || "—";
  document.getElementById("sum-exp").textContent       = EXP_LABELS[profile.experience] || profile.experience;
  document.getElementById("sum-price").textContent     = profile.min_price ? `$${profile.min_price}` : "не задана";
  document.getElementById("sum-excluded").textContent  = profile.excluded.join(", ") || "нет";
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveProfile() {
  const btn = document.getElementById("btn-next");
  btn.disabled = true;
  btn.innerHTML = '<span class="ob-spinner"></span> Сохраняю...';

  const statusEl = document.getElementById("save-status");
  statusEl.classList.remove("hidden", "ob-save-ok", "ob-save-err");

  try {
    const res = await fetch("/api/save-profile", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(profile),
    });

    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = "/login.html";
        return;
      }
      throw new Error(`HTTP ${res.status}`);
    }

    localStorage.setItem("fh_profile", JSON.stringify(profile));

    statusEl.textContent = "✅ Профиль сохранён! Перехожу на дашборд...";
    statusEl.classList.add("ob-save-ok");
    statusEl.classList.remove("hidden");

    setTimeout(() => { window.location.href = "/"; }, 1200);
  } catch (err) {
    localStorage.setItem("fh_profile", JSON.stringify(profile));
    statusEl.textContent = "⚠️ Сохранено локально. Перехожу...";
    statusEl.classList.add("ob-save-err");
    statusEl.classList.remove("hidden");
    setTimeout(() => { window.location.href = "/"; }, 1500);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "💾 Сохранить и начать";
  }
}

function esc(s)     { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function escAttr(s) { return String(s).replace(/'/g,"&#39;").replace(/"/g,"&quot;"); }
