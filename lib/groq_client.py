"""
Groq AI client.

Model: llama-3.3-70b-versatile
  — 70B параметров (vs 8B у предыдущей)
  — Лучшее понимание контекста и нюансов задания
  — Бесплатно на Groq (30 req/min, 14 400/day)
"""

import os
import json
import urllib.request
import urllib.error

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"   # ← лучшая бесплатная модель на Groq

# ── Промпт для анализа ────────────────────────────────────────────────────────
# Улучшен: детальные критерии, учёт ключевых слов, штрафы/бонусы
ANALYZE_PROMPT = """\
Ты — опытный HR-агент фрилансера. Оцени задание строго по критериям профиля.

══ ПРОФИЛЬ ФРИЛАНСЕРА ══════════════════════════════════
Направление : {direction}
Навыки      : {skills}
Опыт        : {experience}
Мин. цена   : ${min_price}
Исключения  : {excluded}

══ ЗАДАНИЕ ═════════════════════════════════════════════
Платформа   : {platform}
Название    : {title}
Описание    : {description}
Цена        : {price}

══ ПРАВИЛА ОЦЕНКИ (строго) ═════════════════════════════
1. Совпадение навыков (+1-4 балла каждый совпавший навык, max 6)
2. Цена:
   - ≥ мин. цены × 1.5      → +2 балла
   - между мин и ×1.5       → +1 балл
   - ниже мин. цены          → -3 балла
   - цена не указана         → -1 балл
3. Опыт:
   - junior: простые задачи → ок, сложные → -2
   - middle/senior: любые → ок
4. Исключения: если слово из списка есть в названии/описании → score = 1, rejected
5. Нет совпадений навыков вообще → score ≤ 3, rejected

══ ШКАЛА ═══════════════════════════════════════════════
8-10 → approved  (явно подходит, стоит откликнуться)
5-7  → review    (есть сомнения, пусть человек решит)
1-4  → rejected  (не подходит)

Ответь ТОЛЬКО валидным JSON, без markdown, без пояснений:
{{"decision": "approved|review|rejected", "score": <1-10>, "reason": "<1-2 предложения на русском, конкретно почему>"}}
"""


class GroqClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")

    def _chat(self, messages: list, max_tokens: int = 300) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY не задан")

        payload = json.dumps({
            "model":      MODEL,
            "messages":   messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,   # почти детерминировано — стабильные оценки
        }).encode()

        req = urllib.request.Request(
            GROQ_URL, data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"].strip()

    def analyze_job(self, job: dict, profile: dict) -> dict:
        """Analyse job vs profile. Returns {decision, score, reason}."""
        direction_labels = {
            "dev":    "Разработка (Python, JS, React и др.)",
            "design": "Дизайн (Figma, UI/UX и др.)",
            "copy":   "Копирайтинг (SEO, статьи и др.)",
            "other":  "Другое",
        }
        exp_labels = {
            "junior": "Начинающий (до 1 года)",
            "middle": "Средний (1-3 года)",
            "senior": "Опытный (3+ года)",
        }

        price = job.get("price")
        price_str = f"${price}" if price else "не указана"

        prompt = ANALYZE_PROMPT.format(
            direction   = direction_labels.get(profile.get("direction",""), profile.get("direction","")),
            skills      = ", ".join(profile.get("skills", [])) or "не указаны",
            experience  = exp_labels.get(profile.get("experience",""), profile.get("experience","")),
            min_price   = profile.get("min_price", 0),
            excluded    = ", ".join(profile.get("excluded", [])) or "нет",
            platform    = job.get("platform", ""),
            title       = job.get("title", ""),
            description = (job.get("description") or "")[:600],
            price       = price_str,
        )

        try:
            raw = self._chat([{"role": "user", "content": prompt}])
            # Strip any markdown fences model might add
            raw = raw.strip()
            for fence in ["```json", "```JSON", "```"]:
                raw = raw.replace(fence, "")
            raw = raw.strip()

            result = json.loads(raw)
            decision = result.get("decision", "review")
            if decision not in ("approved", "review", "rejected"):
                decision = "review"

            return {
                "decision": decision,
                "score":    max(1, min(10, int(result.get("score", 5)))),
                "reason":   result.get("reason", "").strip(),
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[Groq] parse error: {e} | raw: {raw[:200]}")
            return {"decision": "review", "score": 5, "reason": "Не удалось разобрать ответ ИИ"}

        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            raise RuntimeError(f"Groq HTTP {e.code}: {body}") from e
