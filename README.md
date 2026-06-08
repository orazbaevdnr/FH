# 🎯 Freelance Hunter

Автоматический агрегатор фриланс-заказов с ИИ фильтрацией.

Каждые 15 минут парсит FL.ru, анализирует задания через Groq AI
и показывает только те, которые подходят под твой профиль.

**Стек:** Python 3.10 · Vercel Serverless · Vercel KV · Groq AI · Vanilla JS

---

## 🚀 Быстрый старт

### 1. Клонировать и установить

```bash
git clone https://github.com/orazbaevdnr/FH.git
cd FH

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Открой .env и вставь GROQ_API_KEY
```

Получи бесплатный ключ на [console.groq.com](https://console.groq.com).

### 3. Запустить локально

```bash
npm install -g vercel
vercel login
vercel link          # привязать к проекту
vercel dev           # http://localhost:3000
```

---

## ☁️ Деплой на Vercel

### Автоматически (через GitHub)

Любой `git push` в ветку `main` деплоит на продакшен автоматически.

```bash
git add .
git commit -m "feat: your changes"
git push origin main
# → Vercel деплоит автоматически
```

### Вручную

```bash
vercel --prod
```

---

## 🔑 Переменные окружения

| Переменная | Где взять | Env |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | All |
| `KV_REST_API_URL` | Авто после `vercel kv create` | All |
| `KV_REST_API_TOKEN` | Авто после `vercel kv create` | All |

Добавить через CLI:
```bash
vercel env add GROQ_API_KEY
```

---

## 📁 Структура проекта

```
FH/
├── public/
│   ├── index.html          # Дашборд
│   ├── onboarding.html     # 5-шаговый опрос
│   ├── style.css           # Стили (dark theme)
│   ├── app.js              # Логика дашборда
│   └── onboarding.js       # Логика опроса
│
├── api/
│   ├── save-profile.py     # POST — сохранить профиль
│   ├── get-profile.py      # GET  — получить профиль
│   ├── parse-jobs.py       # POST — парсинг FL.ru
│   ├── analyze-jobs.py     # POST — ИИ анализ
│   ├── get-jobs.py         # GET  — список заданий
│   └── update-job.py       # POST — обновить статус
│
├── lib/
│   ├── groq_client.py      # Groq API клиент
│   ├── fl_parser.py        # Парсер FL.ru RSS
│   └── kv_storage.py       # Vercel KV / локальный JSON
│
├── data/
│   └── skills.json         # Навыки по направлениям
│
├── .github/workflows/ci.yml # GitHub Actions
├── vercel.json              # Конфиг Vercel
├── requirements.txt
└── .env.example
```

---

## 🔄 Git workflow

```bash
# Новая фича
git checkout -b feature/habr-parser
# ... правки ...
git add . && git commit -m "feat: add Habr parser"
git push origin feature/habr-parser
# → создать Pull Request → merge в main → автодеплой
```

Ветки:
- `main` → продакшен на `freelance-hunter.vercel.app`
- любая другая ветка → preview deployment

---

## ⏰ Cron Jobs

| Эндпоинт | Расписание | Что делает |
|---|---|---|
| `/api/parse-jobs` | каждые 15 мин | Парсит FL.ru RSS |
| `/api/analyze-jobs` | каждые 16 мин | Groq анализирует pending |

---

## 🛠️ Полезные команды

```bash
vercel logs          # логи продакшена
vercel logs --follow # стрим логов
vercel env ls        # список переменных
vercel kv list       # ключи в базе
vercel rollback      # откат деплоя
```

---

## 📄 License

MIT
