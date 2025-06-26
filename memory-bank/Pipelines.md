# Pipeline d'Extraction de Contenu Lisible

Ce document décrit les flux de travail utilisés dans cette application pour extraire le contenu lisible ("readable") des pages web.

## 1. Flux de `crawl` principal (Rapide et Basique)

Ce flux est initié par la commande `mwi land crawl` et est conçu pour une collecte rapide et à grande échelle.

**Chaîne d'appels :**
`LandController.crawl` → `core.crawl_land` → `core.crawl_expression` → `core.process_expression_content`

**Processus d'extraction :**

1.  **Récupération du HTML** (`crawl_expression`) :
    *   Une requête HTTP est effectuée pour obtenir le HTML brut de l'URL.
    *   **Secours** : En cas d'échec (ex: erreur 404), une tentative est faite pour récupérer une version de la page depuis **Archive.org**.

2.  **Traitement du Contenu** (`process_expression_content`) :
    *   **Nettoyage du HTML** (`clean_html`) : Les balises considérées comme non essentielles sont supprimées (ex: `<script>`, `<footer>`, `<nav>`).
    *   **Extraction du Texte** (`get_readable`) : La méthode `get_text()` de `BeautifulSoup` est utilisée pour extraire tout le texte restant du HTML nettoyé.

**Avantages :**
*   **Rapidité** : Idéal pour traiter un grand volume d'URLs rapidement.
*   **Simplicité** : Ne dépend pas de services externes complexes (sauf pour le secours).

**Inconvénients :**
*   **Qualité variable** : Le contenu extrait peut contenir des éléments non pertinents (publicités, suggestions d'articles, etc.) si le nettoyage initial n'est pas suffisant.

---

## 2. Flux de `readable` dédié (Robuste et de Haute Qualité)

Ce flux est initié par la commande `mwi land readable` et vise à obtenir la meilleure qualité de contenu possible à partir des pages déjà collectées.

**Chaîne d'appels :**
`LandController.readable` → `core.crawl_expression`

**Pipeline d'extraction :**

Le système tente les méthodes suivantes dans l'ordre, s'arrêtant dès qu'un contenu de qualité est obtenu :

1.  **`trafilatura`** :
    *   **Description** : Un outil de pointe spécialisé dans l'extraction de contenu principal, très efficace pour ignorer le "bruit" (menus, pubs, etc.).
    *   **Priorité** : C'est la première et principale méthode utilisée.

2.  **Archive.org + `trafilatura`** :
    *   **Description** : Si les outils échouent sur l'URL en direct, le système recherche une version archivée de la page et y applique `trafilatura`.
    *   **Utilité** : Permet de traiter des pages qui ont changé ou qui ne sont plus accessibles.

4.  **HTML Brut (Dernier recours)** :
    *   **Description** : Si aucune des méthodes ci-dessus ne fonctionne, le HTML brut de la page est stocké.
    *   **Marquage** : Le contenu est préfixé par un commentaire `<!-- PARSER FAILED - RAW HTML -->` pour indiquer l'échec de l'extraction.

**Avantages :**
*   **Haute Qualité** : Fournit un contenu très propre, proche de ce qu'un lecteur humain considérerait comme l'article principal.
*   **Fiabilité** : La combinaison de plusieurs outils et de l'archivage maximise les chances de succès.

**Inconvénients :**
*   **Lenteur** : Le processus est plus lent et consomme plus de ressources.

---

## 3. Pipeline Mercury Parser Autonome (Nouvelle Architecture - 2024)

Ce flux représente une **refonte complète** de la fonction `readable`, conçu comme un système autonome basé exclusivement sur **Mercury Parser**.

**Chaîne d'appels :**
`LandController.readable` → `readable_pipeline.run_readable_pipeline` → `MercuryReadablePipeline.process_land`

**Architecture autonome :**

Le pipeline fonctionne de manière complètement indépendante avec sa propre logique de fusion intelligente :

1.  **Extraction Mercury Parser** :
    *   **Commande** : `mercury-parser <URL> --format=markdown --extract-media --extract-links`
    *   **Contenu** : Extraction markdown native avec préservation des liens et médias
    *   **Métadonnées** : Titre, auteur, date de publication, domaine, nombre de mots
    *   **Robustesse** : Retry automatique avec exponential backoff

2.  **Logique de Fusion Bidirectionnelle** :
    *   **Si base vide + Mercury plein** → Mercury remplit
    *   **Si base pleine + Mercury vide** → Garde la base (s'abstient)
    *   **Si base pleine + Mercury plein** → Applique la stratégie de fusion

3.  **Stratégies de Fusion Configurables** :
    *   **`smart_merge`** (défaut) : Fusion intelligente selon le champ
        - Titres : préfère le plus informatif (plus long)
        - Contenu : Mercury prioritaire (plus propre)
        - Descriptions : garde la plus détaillée
    *   **`mercury_priority`** : Mercury écrase systématiquement
    *   **`preserve_existing`** : Ne touche jamais aux données existantes

4.  **Traitement Enrichi** :
    *   **Médias** : Extraction automatique des images/vidéos depuis le markdown
    *   **Liens** : Création d'ExpressionLink pour les liens trouvés
    *   **Métadonnées** : Mise à jour complète (auteur, date, langue)
    *   **Pertinence** : Recalcul automatique si le contenu change

**Commandes disponibles :**
```bash
# Stratégie par défaut (smart_merge)
python mywi.py land readable --name="MyLand"

# Avec paramètres avancés
python mywi.py land readable --name="MyLand" --limit=100 --depth=2 --merge=smart_merge

# Autres stratégies
python mywi.py land readable --name="MyLand" --merge=mercury_priority
python mywi.py land readable --name="MyLand" --merge=preserve_existing
```

**Avantages :**
*   **Autonomie complète** : Aucune dépendance aux autres extracteurs
*   **Qualité supérieure** : Mercury Parser reste excellent pour l'extraction
*   **Flexibilité** : 3 stratégies pour tous les cas d'usage
*   **Robustesse** : Gestion d'erreurs professionnelle avec retry
*   **Performance** : Traitement parallèle par batch asynchrone
*   **Traçabilité** : Logging complet de toutes les modifications

**Inconvénients :**
*   **Dépendance externe** : Nécessite `mercury-parser` installé (npm)
*   **Lenteur relative** : Plus lent que le crawl basique

---

## Synthèse et Recommandations

| Caractéristique | Flux `crawl` | Flux `readable` (legacy) | **Pipeline Mercury (nouveau)** |
| :--- | :--- | :--- | :--- |
| **Objectif** | Collecte rapide | Haute qualité | **Extraction autonome enrichie** |
| **Qualité** | Basique | Élevée | **Très élevée** |
| **Vitesse** | Rapide | Lente | **Moyenne** |
| **Outils** | `BeautifulSoup` | `trafilatura` | **`mercury-parser`** |
| **Flexibilité** | Aucune | Faible | **3 stratégies configurables** |
| **Médias/Liens** | Non | Non | **Oui (automatique)** |
| **Cas d'usage** | Collecte initiale | Analyse approfondie | **Production, migration, enrichissement** |

**Recommandations :**

1. **Flux `crawl`** : Collecte initiale et évaluation de la pertinence
2. **Pipeline Mercury** : **Production standard** - remplace le flux readable legacy
3. **Flux `readable` legacy** : Fallback uniquement si Mercury indisponible

Le **Pipeline Mercury Parser autonome** représente l'évolution moderne du système d'extraction, apportant robustesse, flexibilité et qualité d'extraction tout en préservant la simplicité d'utilisation.

Lorsqu'un contenu est extrait avec succès par le pipeline Mercury, le champ `readable_at` de l'expression est mis à jour avec la date et l'heure actuelles, et la pertinence est recalculée automatiquement.
