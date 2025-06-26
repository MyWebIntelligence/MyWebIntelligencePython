# Pipeline d'Extraction de Contenu Lisible

Ce document décrit les deux principaux flux de travail utilisés dans cette application pour extraire le contenu lisible ("readable") des pages web.

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

## Synthèse et Recommandations

| Caractéristique | Flux `crawl` | Flux `readable` |
| :--- | :--- | :--- |
| **Objectif** | Collecte rapide de données | Extraction de contenu de haute qualité |
| **Qualité** | Basique | Élevée |
| **Vitesse** | Rapide | Lente |
| **Outils** | `BeautifulSoup.get_text()` | `trafilatura` |
| **Cas d'usage** | Première passe sur un grand corpus | Analyse de texte approfondie, préparation de corpus |

En résumé, le flux de **`crawl`** est utilisé pour la **collecte initiale et l'évaluation de la pertinence**, tandis que le flux de **`readable`** est utilisé pour le **nettoyage et le raffinage du contenu** en vue d'une analyse plus poussée.

Lorsqu'un contenu est extrait avec succès par l'un des outils du pipeline `readable` (`trafilatura`, ou via `Archive.org`), le champ `approved_at` de l'expression est mis à jour avec la date et l'heure actuelles, signifiant qu'une version lisible du contenu a été obtenue et stockée.
