# Plan d'implémentation - Feature Analyse Média MyWebIntelligence

## Vue d'ensemble du projet

L'analyse média est une fonctionnalité majeure qui enrichit MyWebIntelligence avec la capacité d'extraire, analyser et gérer automatiquement les médias (images, vidéos, audio) collectés pendant le crawl. 

### Objectifs principaux
- **Analyse automatique** des images pendant le crawl
- **Extraction de métadonnées** : dimensions, taille, format, couleurs dominantes, EXIF
- **Filtrage intelligent** et suppression basés sur des critères configurables
- **Statistiques avancées** et détection de doublons
- **Performance optimisée** avec traitement par batch asynchrone

## Phase 1 : Infrastructure de base ✅

### 1.1 Migration de base de données ✅
- [x] **Fichier** : `migrations/001_add_media_analysis.py`
- [x] **Statut** : Terminé
- [x] **Contenu** :
  - Script de migration avec vérification des colonnes existantes
  - Ajout de 12 nouvelles colonnes au modèle Media
  - Création d'index pour optimiser les performances
  - Gestionnaire de migrations intégré

### 1.2 Mise à jour du modèle de données ✅
- [x] **Fichier** : `mwi/model.py`
- [x] **Statut** : Terminé
- [x] **Actions requises** :
  - Enrichir la classe Media avec les nouveaux champs
  - Ajouter les méthodes helper (is_conforming, get_dominant_colors_list, etc.)
  - Mettre à jour les index et contraintes

### 1.3 Configuration système ✅
- [x] **Fichier** : `settings.py`
- [x] **Statut** : Terminé
- [x] **Actions requises** :
  - Ajouter les paramètres de configuration média
  - Définir les valeurs par défaut
  - Configurer les filtres et limites

## Phase 2 : Module d'analyse principal ✅

### 2.1 Analyseur de médias ✅
- [x] **Fichier** : `mwi/media_analyzer.py`
- [x] **Statut** : Terminé
- [x] **Fonctionnalités implémentées** :
  - Classe MediaAnalyzer complète (~500 lignes)
  - Extraction de métadonnées (dimensions, format, couleurs)
  - Analyse EXIF et hash perceptuel
  - Détection de contenu (logos, screenshots, texte)
  - Gestion robuste d'erreurs avec retry
  - Filtrage par patterns d'exclusion

### 2.2 Requêtes analytiques ✅
- [x] **Fichier** : `mwi/queries.py`
- [x] **Statut** : Terminé
- [x] **Actions requises** :
  - Créer le module de requêtes analytiques
  - Implémenter les statistiques média
  - Fonctions de détection de doublons
  - Requêtes de prévisualisation de suppression

## Phase 3 : Intégration dans le système existant

### 3.1 Modification du core
- [ ] **Fichier** : `mwi/core.py`
- [ ] **Statut** : En cours
- [ ] **Priorité** : Haute
- [ ] **Actions requises** :
  - Modifier `process_expression_content` pour l'analyse média synchrone
  - Créer `crawl_land_with_media_analysis` pour l'analyse asynchrone
  - Implémenter `extract_and_analyze_medias`
  - Ajouter les fonctions de réanalyse et suppression

### 3.2 Mise à jour des contrôleurs
- [ ] **Fichier** : `mwi/controller.py`
- [ ] **Statut** : À faire
- [ ] **Priorité** : Haute
- [ ] **Actions requises** :
  - Ajouter `reanalyze_media` dans LandController
  - Implémenter `preview_media_deletion`
  - Créer `media_stats`
  - Modifier `crawl` pour supporter l'option analyse média

### 3.3 Interface CLI
- [ ] **Fichier** : `mwi/cli.py`
- [ ] **Statut** : À faire
- [ ] **Priorité** : Moyenne
- [ ] **Actions requises** :
  - Ajouter les nouveaux arguments CLI (--minwidth, --minheight, etc.)
  - Mettre à jour le dispatch pour les nouvelles commandes
  - Ajouter la commande de migration `db migrate`

## Phase 4 : Fonctionnalités avancées

### 4.1 Export enrichi
- [ ] **Fichier** : `mwi/export.py`
- [ ] **Statut** : À modifier
- [ ] **Priorité** : Moyenne
- [ ] **Actions requises** :
  - Enrichir l'export `mediacsv` avec toutes les métadonnées
  - Optimiser les requêtes d'export
  - Supporter les filtres par critères média

### 4.2 Configuration avancée
- [ ] **Fichier** : `settings.py`
- [ ] **Statut** : Partiel
- [ ] **Actions requises** :
  - Paramètres de filtrage (min/max dimensions, taille)
  - Configuration des timeouts et retry
  - Options d'analyse (couleurs, EXIF, contenu)

## Phase 5 : Tests et validation

### 5.1 Tests unitaires
- [ ] **Fichiers** : `tests/test_media_*.py`
- [ ] **Statut** : À créer
- [ ] **Priorité** : Haute
- [ ] **Contenu requis** :
  - Tests pour MediaAnalyzer
  - Tests d'intégration pour le crawl
  - Tests CLI pour les nouvelles commandes
  - Tests de migration

### 5.2 Tests d'intégration
- [ ] **Validation** du pipeline complet
- [ ] **Tests** de performance sur gros volumes
- [ ] **Validation** des exports enrichis

## Phase 6 : Documentation et déploiement

### 6.1 Documentation utilisateur
- [ ] **Fichier** : Mise à jour du README principal
- [ ] **Guide** d'installation des dépendances
- [ ] **Exemples** d'utilisation
- [ ] **Troubleshooting**

### 6.2 Documentation technique
- [ ] **Architecture** détaillée
- [ ] **API** des nouvelles fonctions
- [ ] **Configuration** avancée

## Dépendances et prérequis

### Dépendances Python à ajouter
```bash
pip install Pillow==10.1.0
pip install imagehash==4.3.1  
pip install numpy==1.24.3
pip install scikit-learn==1.3.0
```

### Dépendances système
- Aucune dépendance externe système requise
- Compatible avec l'architecture Docker existante

## Planning estimé

### Sprint 1 (1-2 jours) - Infrastructure ✅
- [x] Migration database ✅
- [x] Module MediaAnalyzer ✅

### Sprint 2 (2-3 jours) - Intégration core
- [ ] Mise à jour du modèle
- [ ] Modification de core.py
- [ ] Module queries.py

### Sprint 3 (1-2 jours) - Interface utilisateur
- [ ] Contrôleurs
- [ ] CLI
- [ ] Configuration

### Sprint 4 (1-2 jours) - Tests et validation
- [ ] Tests unitaires
- [ ] Tests d'intégration
- [ ] Validation performance

### Sprint 5 (1 jour) - Documentation
- [ ] Documentation utilisateur
- [ ] Guide de migration
- [ ] Exemples d'usage

## Commandes disponibles après implémentation

```bash
# Migration initiale
python mywi.py db migrate

# Crawl avec analyse média
python mywi.py land crawl --name=PROJECT --analyze-media

# Réanalyse des médias existants
python mywi.py land reanalyze --name=PROJECT

# Filtrage et suppression
python mywi.py land reanalyze --name=PROJECT --minwidth=300 --minheight=300 --suppress

# Prévisualisation des suppressions
python mywi.py land preview_deletion --name=PROJECT --minwidth=200 --maxsize=5

# Statistiques
python mywi.py land media_stats --name=PROJECT

# Export enrichi
python mywi.py land export --name=PROJECT --type=mediacsv
```

## Risques identifiés et mitigation

### Risques techniques
1. **Performance** sur gros volumes d'images
   - *Mitigation* : Traitement par batch asynchrone
   
2. **Consommation mémoire** lors de l'analyse
   - *Mitigation* : Redimensionnement automatique des images

3. **Erreurs de téléchargement** d'images
   - *Mitigation* : Retry avec exponential backoff

### Risques fonctionnels
1. **Suppression accidentelle** de médias importants
   - *Mitigation* : Mode prévisualisation obligatoire

2. **Compatibilité** avec bases existantes
   - *Mitigation* : Migration non-destructive avec vérifications

## Métriques de succès

### Métriques techniques
- **Taux de succès** d'analyse > 95%
- **Performance** : <10s pour 100 images moyennes
- **Couverture** de tests > 80%

### Métriques fonctionnelles  
- **Réduction** du bruit (petites images) > 50%
- **Détection** de doublons effective
- **Enrichissement** des exports avec métadonnées complètes

## Points d'attention

### Compatibilité ascendante
- Tous les exports existants restent fonctionnels
- Les crawls sans analyse média continuent de fonctionner
- Migration transparente pour les utilisateurs existants

### Extensibilité
- Architecture modulaire permettant l'ajout de nouveaux analyseurs
- Support futur pour l'analyse de contenu avec ML
- Interface extensible pour d'autres types de médias

## Prochaines étapes immédiates

1. **Compléter le modèle** dans `mwi/model.py`
2. **Créer le module queries** dans `mwi/queries.py`  
3. **Modifier core.py** pour intégrer l'analyse
4. **Tester la migration** sur une base de test
5. **Implémenter les contrôleurs** et CLI

Cette feature représente une évolution majeure de MyWebIntelligence, apportant des capacités d'analyse avancées tout en préservant la simplicité d'utilisation existante.
