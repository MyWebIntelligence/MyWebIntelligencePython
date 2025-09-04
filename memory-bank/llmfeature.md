# MyWebIntelligence – Plan Agentic: Filtrage de pertinence via OpenRouter (oui/non)

Objectif: introduire un garde‑fou IA, optionnel et configurable, qui juge si une page est pertinente pour un projet (« oui/non ») avant le calcul de pertinence classique. Si « non »: on fixe `relevance=0` et on court‑circuite le calcul; si « oui »: on calcule la pertinence existante. Intégration minimale, réversible, sans changement de schéma.

---

## 1. Portée & Résultats attendus

- Fonctionnalité: évaluer la pertinence binaire (« oui/non ») via OpenRouter au moment où `readable` est mis à jour par le pipeline Mercury.
- Activation: feature flag `settings.openrouter_enabled` (désactivé par défaut), API key + modèle configurables.
- Impact: gating appliqué partout où la relevance est calculée (crawl initial et fallbacks dans `mwi/core.py`, consolidation, pipeline `mwi/readable_pipeline.py`), à l’exclusion du recalcul massif `land_relevance` (ex: `land addterm`).
- Résultat: pages jugées « non » n’entrent pas dans l’analyse (relevance=0, pas d’approbation, pas de médias dynamiques ni de liens).
- Non‑objectifs: pas d’ajout de colonnes DB; pas de cache persistant; pas d’appel OpenRouter dans `land_relevance` (post‑ajout de termes).

---

## 2. Carte d’impact (fichiers)

- `settings.py`
  - Ajout des variables: `openrouter_enabled`, `openrouter_api_key`, `openrouter_model`, `openrouter_timeout`, `openrouter_readable_max_chars`, `openrouter_max_calls_per_run` (avec overrides via env `MWI_*`).
  - Aucun comportement par défaut changé si désactivé (False/None).

- `mwi/llm_openrouter.py` (NOUVEAU)
  - Client OpenRouter (construction de prompt, POST `chat/completions`, parsing réponse, normalisation oui/non, troncature du readable, budget d’appels par run).
  - Fonctions exposées: `is_relevant_via_openrouter(land, expression) -> Optional[bool]` + utilitaires (prompt, normalisation, collecte mots‑clés).

- `mwi/readable_pipeline.py`
  - `_apply_updates(...)`: insérer le garde‑fou AVANT `_calculate_relevance(...)` quand `readable` a changé.
  - Politique: « non » explicite → `relevance=0`; « oui » ou réponse ambigüe/erreur → calcul local normal.

- `mwi/core.py` (gating hors recalcul massif)
  - Appliquer le garde‑fou avant chaque assignation de relevance dans les flows opérationnels:
    - Finalisation crawl/extraction: lignes autour de `expression.relevance = expression_relevance(...)` (ex. `mwi/core.py:830`, `:1102`).
    - Fallbacks HTML/Archive/Trafilatura: mêmes blocs de finalisation.
    - Consolidation: `mwi/core.py:904` avant `expr.relevance = expression_relevance(...)`.
  - Exclure explicitement le recalcul massif `land_relevance` (ex. `mwi/core.py:1475+`).
  - Idée d’implémentation: petit helper local `compute_relevance_with_gate(dictionary, expression)` (wrap du calcul + OpenRouter) pour limiter la duplication.

- `tests/` (recommandé)
  - `tests/test_openrouter_gate.py`: mocks `requests.post` pour couvrir oui/non/erreur; tests ciblés sur `readable_pipeline` et un point dans `core.py` (crawl finalisation) pour valider l’intégration.

- `README.md`
  - Section « Filtrage IA (OpenRouter) »: variables d’environnement, activation, limites, comportement (seulement « non » bloque). Indication sur l’exclusion du recalcul massif.

- (Optionnel) `mwi/controller.py`
  - Si souhaité plus tard: ajout d’un flag CLI `--openrouter on|off` pour override ponctuel (hors MVP). 

---

## 3. Configuration (settings.py)

Ajouter des variables avec override par variables d’environnement, valeurs sûres par défaut:

```python
# OpenRouter relevance gate (disabled by default)
openrouter_enabled = os.environ.get("MWI_OPENROUTER_ENABLED", "false").lower() in ("1", "true", "yes")
openrouter_api_key = os.environ.get("MWI_OPENROUTER_API_KEY", None)
openrouter_model = os.environ.get("MWI_OPENROUTER_MODEL", None)  # ex: "openai/gpt-4o-mini" ou "anthropic/claude-3-haiku"
openrouter_timeout = int(os.environ.get("MWI_OPENROUTER_TIMEOUT", "15"))  # seconds
# bornes pour maîtriser coût/latence
openrouter_readable_max_chars = int(os.environ.get("MWI_OPENROUTER_READABLE_MAX_CHARS", "12000"))
openrouter_max_calls_per_run = int(os.environ.get("MWI_OPENROUTER_MAX_CALLS_PER_RUN", "500"))
```

Règles:
- Si `openrouter_enabled` est False, aucun appel réseau n’est effectué.
- Si clé ou modèle absents: désactiver silencieusement la fonctionnalité (log d’avertissement et fallback local).

---

## 4. Client OpenRouter (mwi/llm_openrouter.py)

Créer un module dédié pour isoler I/O réseau et faciliter le mock en test.

Fonctions proposées:
- `build_relevance_prompt(land, expression, readable_text: str) -> str`: construit le prompt conforme.
- `ask_openrouter_yesno(prompt: str) -> str`: envoie la requête `chat/completions` et retourne le texte renvoyé par l’assistant.
- `is_relevant_via_openrouter(land, expression) -> Optional[bool]`: gère truncation, construction du prompt, appel API, et normalisation (« oui »=True, « non »=False, sinon None).

Spécifications d’implémentation:
- Endpoint: `POST https://openrouter.ai/api/v1/chat/completions`
- Header: `Authorization: Bearer <settings.openrouter_api_key>`; `Content-Type: application/json`
- Body:
```json
{
  "model": "<settings.openrouter_model>",
  "messages": [{"role": "user", "content": "<prompt>"}],
  "temperature": 0
}
```
- Timeout: `settings.openrouter_timeout` (avec `requests`)
- Normalisation: `content.strip().lower()`
  - retourne False si commence exactement par "non" ou == "no"
  - retourne True si commence par "oui" ou == "yes"
  - sinon `None` (réponse ambigüe)
- Troncature: `readable[:settings.openrouter_readable_max_chars]` si nécessaire.
- Garde‑fous: compteur d’appels en mémoire pour respecter `openrouter_max_calls_per_run`.
- Logs (via `print` pour rester cohérent avec le code): afficher OUI/NON/erreurs succincts.

Prompt (FR, strict oui/non) — respecter la langue du land si dispo; par défaut FR:

```
Dans le cadre de la constitution d'un corpus de pages Web à des fins d'analyse de contenu, nous voulons savoir si la page crawlée est pertinente pour le projet ou non.
Le projet a les caractéristiques suivantes :
- Nom du projet : {land.name}
- Description : {land.description}
- Mots clés : {liste_mots_cles}
- Langue : {land.lang}
La page suivante :
- URL = {expression.url}
- Titre : {expression.title}
- Description : {expression.description}
- Readable (extrait) : {readable_tronque}
Tu répondras ABSOLUMENT et uniquement par "oui" ou "non" sans aucun commentaire.
```

Notes:
- `liste_mots_cles` = concaténation des `Word.term` liés au `Land` (via `LandDictionary`).
- On peut réduire le `readable` à un extrait pour rester sous les limites de contexte.

---

## 5. Intégration pipeline (mwi/readable_pipeline.py)

Emplacement: method `_apply_updates(...)` juste après la détection de changement `readable` et avant `_calculate_relevance(...)`.

Pseudo‑code minimal:

```python
from . import model
import settings

try:
    if 'readable' in update.field_updates:
        relevance = None
        if settings.openrouter_enabled and settings.openrouter_api_key and settings.openrouter_model:
            from .llm_openrouter import is_relevant_via_openrouter
            verdict = is_relevant_via_openrouter(expression.land, expression)  # True/False/None
            if verdict is False:
                relevance = 0
                print(f"OpenRouter gate: NON -> relevance=0 for {expression.url}")
            else:
                relevance = self._calculate_relevance(dictionary, expression)
                print(f"OpenRouter gate: {('OUI' if verdict else 'INCONNU')} -> computed relevance={relevance} for {expression.url}")
        else:
            relevance = self._calculate_relevance(dictionary, expression)
        expression.relevance = relevance
        if relevance and relevance > 0:
            expression.approved_at = datetime.now()
except Exception as e:
    # Sécurité: ne jamais bloquer le pipeline; fallback au calcul local
    print(f"OpenRouter gate error for {expression.url}: {e}")
    relevance = self._calculate_relevance(dictionary, expression)
    expression.relevance = relevance
    if relevance and relevance > 0:
        expression.approved_at = datetime.now()
```

Politique d’erreur/ambiguïté:
- Erreur réseau/timeout/quota → fallback sur calcul local (ne pas bloquer le flux).
- Réponse ambigüe (ni « oui » ni « non ») → calcul local.
- Seul un « non » explicite court‑circuite le calcul.

---

## 6. Choix de propagation (où appeler OpenRouter ?)

- OUI: lors de la mise à jour initiale de `readable` par le pipeline Mercury (première intégration du contenu).
- NON: lors de `land addterm` → recalcul massif de `relevance` avec la méthode actuelle uniquement (coûts API autrement prohibitifs et peu pertinents).
- Évolution possible: un flag CLI pour forcer/désactiver OpenRouter à l’exécution `land readable` (hors scope MVP).

---

## 7. Tests & Validation

Unitaires (mock `requests.post`):
- Cas « non » → `is_relevant_via_openrouter` renvoie False; `_apply_updates` fixe `relevance=0`, ne positionne pas `approved_at`.
- Cas « oui » → renvoie True; `_apply_updates` appelle `_calculate_relevance` (>0 attendu selon contenu) et pose `approved_at`.
- Cas ambigü → renvoie None; fallback au calcul local.
- Cas erreur (timeout, 500, JSON invalide) → exception capturée; fallback au calcul local.

Intégration légère:
- Activer `MWI_OPENROUTER_ENABLED=1` + clé factice mockée; injecter un mock HTTP sur l’endpoint; dérouler `python mywi.py land readable --name=...` et assert sur les champs `relevance/approved_at`.

Smoke manual (sans réseau):
- `openrouter_enabled=False` → aucun changement de comportement.
- Deux URLs (pertinente/hors sujet), check exports CSV: page non pertinente absente si `minrel>0`.

---

## 8. Performance, coûts, sûreté

- `openrouter_max_calls_per_run`: borne dure pour éviter les dérives (arrêt du gating au‑delà, logs d’avertissement).
- `openrouter_readable_max_chars`: limiter la taille du prompt pour éviter les dépassements de contexte et contenir les coûts.
- Parallelisme: garder l’appel séquentiel par expression lors de la phase `_apply_updates` (c’est déjà un goulot raisonnable après Mercury). Évolution: batch asynchrone si nécessaire.
- Logs concis: « OpenRouter gate: OUI/NON/INCONNU/ERROR … »
- Sécurité: clé injectée par variable d’environnement; ne jamais commiter la clé.

---

## 9. Étapes de livraison (patchs minimaux)

1) `settings.py`
- Ajouter les 6 variables `openrouter_*` avec override env.

2) `mwi/llm_openrouter.py`
- Implémenter: compteur d’appels, troncature `readable`, construction `liste_mots_cles`, prompt, appel `requests.post`, parsing JSON, normalisation oui/non, gestion erreurs.

3) `mwi/readable_pipeline.py`
- Import conditionnel + garde‑fou dans `_apply_updates` avant `_calculate_relevance`.

4) `tests/test_openrouter_gate.py` (optionnel mais recommandé)
- 3 tests unitaires (oui/non/erreur) avec mock.

5) `README.md`
- Section « Filtrage IA (OpenRouter) »: variables d’environnement, activation, comportement, limites.

Rollback: mettre `MWI_OPENROUTER_ENABLED=0` (ou retirer clé/modèle) → aucun appel réseau, comportement historique restauré.

---

## 10. Exemples d’implémentation (snippets)

Récupération des mots‑clés du land:

```python
from . import model

def get_land_terms(land: model.Land) -> list[str]:
    rows = (model.Word.select(model.Word.term)
            .join(model.LandDictionary)
            .where(model.LandDictionary.land == land))
    return [r.term for r in rows]
```

Normalisation réponse:

```python
def normalize_yesno(text: str) -> str:
    t = text.strip().lower()
    if t.startswith("non") or t == "no":
        return "non"
    if t.startswith("oui") or t == "yes":
        return "oui"
    return "?"
```

---

## 11. Acceptation (Done Criteria)

- Paramètres dispo dans `settings.py` + doc.
- Gating actif uniquement si `openrouter_enabled=True` ET clé ET modèle.
- Pages « non »: `relevance=0`, pas d’`approved_at`, exclues des exports avec `minrel>0` et des étapes aval (médias dynamiques, liens).
- En cas d’erreur réseau: pipeline non bloquant, fallback local.
- Aucune régression quand désactivé.

---

## 12. Commandes utiles (validation)

- Initialisation: `python mywi.py db setup`
- Pipeline readable (sans OpenRouter): `python mywi.py land readable --name=LAND`
- Activation OpenRouter (ex.):
  - `export MWI_OPENROUTER_ENABLED=1`
  - `export MWI_OPENROUTER_API_KEY=sk-...`
  - `export MWI_OPENROUTER_MODEL=openai/gpt-4o-mini`
  - `python mywi.py land readable --name=LAND`
- Export de contrôle: `python mywi.py land export --name=LAND --type=pagecsv --minrel 1`

---

## 13. Extensions futures

- Flag CLI `--openrouter=on|off` pour override ponctuel.
- Caching en mémoire par run basé sur `(url, hash(dico))`.
- Support multi‑langues du prompt (FR/EN selon `land.lang`).
- Batch async (si limites API compatibles) + backoff adaptatif.
- Journaux structurés (niveau et métriques d’appel) si passage à `logging` standard.

---

En appliquant ces étapes, on introduit un filtrage IA oui/non en amont, sans modifier le cœur métier de la pertinence pondérée, et sans fragiliser le pipeline: désactivable instantanément, sans régression lorsque coupé, et maîtrisé en coûts/latence.
