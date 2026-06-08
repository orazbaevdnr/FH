"""
Groq AI client — llama-3.3-70b-versatile.
Fixes:
  - Batch-safe (caller controls rate limiting)
  - Robust JSON extraction (handles markdown fences)
  - Smarter price handling (0 = unknown, not penalty-worthy)
  - Concise but accurate prompt — less token waste
"""

import os
import json
import urllib.request
import urllib.error
import re

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"   # 70B, best free Groq model

# ── System prompt (sets up the role firmly) ───────────────────────────────────
SYSTEM_PROMPT = """\
Ты — HR-агент фрилансера. Твоя задача: оценить задание и решить, стоит ли откликаться.
Отвечай СТРОГО JSON, без markdown, без пояснений вне JSON.
Формат: {"decision": "approved|review|rejected", "score": <1-10>, "reason": "<2-3 предложения на русском>"}
"""

# ── User prompt (filled per-job) ──────────────────────────────────────────────
ANALYZE_PROMPT = """\
## ПРОФИЛЬ ФРИЛАНСЕРА
- Направление: {direction}
- Навыки: {skills}
- Опыт: {experience}
- Мин. ставка: {min_price_str}
- Исключения (стоп-слова): {excluded}

## ЗАДАНИЕ
- Платформа: {platform}
- Название: {title}
- Описание: {description}
- Бюджет: {price_str}

## ПРАВИЛА ОЦЕНКИ
Начни с 5 баллов, затем применяй корректировки:

НАВЫКИ (главный критерий):
  +2 за каждый совпавший навык (макс +6)
  −4 если совпадений нет вообще → score ≤ 3

БЮДЖЕТ:
  Если указан и ≥ мин. ставки × 1.5 → +2
  Если между мин. ставкой и ×1.5   → +1
  Если ниже мин. ставки            → −3
  Если не указан (0 или "?")       → 0 (нейтрально, не штраф)

СТОП-СЛОВА (исключения):
  Если любое стоп-слово есть в названии или описании → score = 1, decision = "rejected"

ОПЫТ:
  junior + явно сложный проект (архитектура, senior-level) → −1
  middle/senior → без изменений

ИТОГ:
  8-10 → approved  (явно подходит, отвечай!)
  5-7  → review    (сомнения, пусть фрилансер решит)
  1-4  → rejected  (не подходит)

Ответь только JSON, ничего лишнего.
"""


class GroqClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")

    def _chat(self, system: str, user: str, max_tokens: int = 256) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY не задан")

        payload = json.dumps({
            "model":       MODEL,
            "messages":    [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens":  max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},  # force JSON mode
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
        """Returns {decision, score, reason}."""
        direction_labels = {
            "dev":    "Разработка (Python, JS, React, и т.д.)",
            "design": "Дизайн (Figma, UI/UX, графика)",
            "copy":   "Копирайтинг (SEO, статьи, тексты)",
            "other":  "Другое",
        }
        exp_labels = {
            "junior": "Junior (до 1 года)",
            "middle": "Middle (1–3 года)",
            "senior": "Senior (3+ года)",
        }

        price = job.get("price") or 0
        min_price = int(profile.get("min_price") or 0)

        # Describe price in human-readable form for the prompt
        if price and price > 0:
            price_str = f"${price}"
        else:
            price_str = "не указан"

        # Describe min price
        if min_price > 0:
            min_price_str = f"${min_price}/проект"
        else:
            min_price_str = "не задана"

        prompt = ANALYZE_PROMPT.format(
            direction   = direction_labels.get(profile.get("direction", ""), profile.get("direction", "")),
            skills      = ", ".join(profile.get("skills", [])) or "не указаны",
            experience  = exp_labels.get(profile.get("experience", ""), profile.get("experience", "")),
            min_price_str = min_price_str,
            excluded    = ", ".join(profile.get("excluded", [])) or "нет",
            platform    = job.get("platform", ""),
            title       = job.get("title", "")[:200],
            description = (job.get("description") or "")[:800],
            price_str   = price_str,
        )

        try:
            raw = self._chat(SYSTEM_PROMPT, prompt)

            # Strip accidental markdown fences
            raw = re.sub(r"```(?:json)?", "", raw).strip()

            result = json.loads(raw)
            decision = result.get("decision", "review")
            if decision not in ("approved", "review", "rejected"):
                decision = "review"

            score = result.get("score", 5)
            try:
                score = max(1, min(10, int(score)))
            except (TypeError, ValueError):
                score = 5

            reason = str(result.get("reason", "")).strip()[:400]

            return {"decision": decision, "score": score, "reason": reason}

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[Groq] parse error: {e} | raw={repr(raw[:200])}")
            return {"decision": "review", "score": 5, "reason": "Не удалось разобрать ответ ИИ"}

        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:400]
            raise RuntimeError(f"Groq HTTP {e.code}: {body}") from e
