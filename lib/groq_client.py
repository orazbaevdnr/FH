import os
import json
import urllib.request
import urllib.error

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

ANALYZE_PROMPT = """Оцени фриланс-задание и верни ТОЛЬКО JSON без markdown.

ЗАДАНИЕ:
Название: {title}
Описание: {description}
Цена: {price}

ПРОФИЛЬ ФРИЛАНСЕРА:
Направление: {direction}
Навыки: {skills}
Опыт: {experience}
Мин. цена: ${min_price}
Исключения: {excluded}

Правила оценки:
- 8-10 → approved (отлично подходит по навыкам и цене)
- 5-7  → review (частично подходит, стоит посмотреть)
- 1-4  → rejected (не подходит или в исключениях)

Если цена ниже минимальной — снизь оценку на 2-3 балла.
Если тема в исключениях — сразу rejected.

Ответ строго в формате:
{{"decision": "approved|review|rejected", "score": 1-10, "reason": "1-2 предложения на русском"}}"""


class GroqClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")

    def _request(self, messages: list, max_tokens: int = 256) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY не задан")

        payload = json.dumps({
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }).encode()

        req = urllib.request.Request(
            GROQ_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()

    def analyze_job(self, job: dict, profile: dict) -> dict:
        """Analyze job against user profile. Returns decision dict."""
        prompt = ANALYZE_PROMPT.format(
            title=job.get("title", ""),
            description=(job.get("description", "") or "")[:500],
            price=job.get("price", "не указана"),
            direction=profile.get("direction", ""),
            skills=", ".join(profile.get("skills", [])),
            experience=profile.get("experience", ""),
            min_price=profile.get("min_price", 0),
            excluded=", ".join(profile.get("excluded", [])) or "нет",
        )

        try:
            raw = self._request([{"role": "user", "content": prompt}])
            # Strip markdown code fences if model added them
            raw = raw.strip().strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            result = json.loads(raw)
            return {
                "decision": result.get("decision", "review"),
                "score": max(1, min(10, int(result.get("score", 5)))),
                "reason": result.get("reason", ""),
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {"decision": "review", "score": 5, "reason": f"Ошибка анализа: {e}"}
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Groq HTTP {e.code}: {e.read().decode()}") from e
