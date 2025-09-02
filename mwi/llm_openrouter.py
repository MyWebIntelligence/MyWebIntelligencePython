import json
from typing import Optional, List

import requests

from . import model
import settings


_call_count = 0


def _get_land_terms(land: model.Land) -> List[str]:
    rows = (
        model.Word.select(model.Word.term)
        .join(model.LandDictionary)
        .where(model.LandDictionary.land == land)
    )
    return [r.term for r in rows]


def build_relevance_prompt(land: model.Land, expression: model.Expression, readable_text: str) -> str:
    terms = ", ".join(_get_land_terms(land))
    title = str(getattr(expression, "title", "") or "")
    desc = str(getattr(expression, "description", "") or "")
    url = str(getattr(expression, "url", "") or "")
    land_desc = str(getattr(land, "description", "") or "")

    prompt = (
        "Dans le cadre de la constitution d'un corpus de pages Web à des fins d'analyse de contenu, "
        "nous voulons savoir si la page crawlée est pertinente pour le projet ou non.\n"
        "Le projet a les caractéristiques suivantes :\n"
        f"- Nom du projet : {land.name}\n"
        f"- Description : {land_desc}\n"
        f"- Mots clés : {terms}\n"
        "La page suivante :\n"
        f"- URL = {url}\n"
        f"- Titre : {title}\n"
        f"- Description : {desc}\n"
        f"- Readable (extrait) : {readable_text}\n"
        "Tu répondras ABSOLUMENT et uniquement par \"oui\" ou \"non\" sans aucun commentaire."
    )
    return prompt


def _normalize_yesno(text: str) -> str:
    t = (text or "").strip().lower()
    if t.startswith("non") or t == "no":
        return "non"
    if t.startswith("oui") or t == "yes":
        return "oui"
    return "?"


def ask_openrouter_yesno(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(body),
        timeout=settings.openrouter_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def is_relevant_via_openrouter(land: model.Land, expression: model.Expression) -> Optional[bool]:
    global _call_count

    # Preconditions
    if not getattr(settings, "openrouter_enabled", False):
        return None
    if not settings.openrouter_api_key or not settings.openrouter_model:
        print("OpenRouter disabled: missing API key or model")
        return None
    if _call_count >= settings.openrouter_max_calls_per_run:
        print("OpenRouter budget reached for this run; skipping gate")
        return None

    readable_text = str(getattr(expression, "readable", "") or "")
    if readable_text:
        readable_text = readable_text[: settings.openrouter_readable_max_chars]
    else:
        # Fallback to a minimal context if readable is missing
        readable_text = ""

    prompt = build_relevance_prompt(land, expression, readable_text)

    try:
        _call_count += 1
        content = ask_openrouter_yesno(prompt)
        verdict = _normalize_yesno(content)
        if verdict == "non":
            print(f"OpenRouter gate verdict=NON for {expression.url}")
            return False
        if verdict == "oui":
            print(f"OpenRouter gate verdict=OUI for {expression.url}")
            return True
        print(f"OpenRouter gate verdict=INCONNU for {expression.url}: '{content[:50]}...'")
        return None
    except Exception as e:
        print(f"OpenRouter gate error for {expression.url}: {e}")
        return None

