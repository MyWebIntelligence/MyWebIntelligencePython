# Plan de développement - Pipeline readable Mercury Parser autonome

## Architecture du nouveau pipeline readable

### Vue d'ensemble

Le nouveau pipeline `readable` sera une refonte complète basée sur Mercury Parser, conçu comme un système autonome de mise à jour enrichie des expressions en base de données. Le pipeline implémentera une logique de fusion intelligente pour optimiser la qualité des données.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Expression    │────▶│  Mercury Parser  │────▶│ Fusion Engine   │
│   Repository    │     │   (markdown +    │     │  (Smart Merge)  │
└─────────────────┘     │     media)       │     └─────────────────┘
                        └──────────────────┘              │
                                                         ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Update Engine   │◀────│ Validation &    │
                        │  (DB Update)     │     │ Quality Check   │
                        └──────────────────┘     └─────────────────┘
```

## Structure du code - Nouveau module `mwi/readable_pipeline.py`

```python
"""
Mercury Parser Readable Pipeline - Système autonome d'enrichissement
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from . import model
from .core import get_land_dictionary


class MergeStrategy(Enum):
    """Stratégies de fusion des données"""
    MERCURY_PRIORITY = "mercury_priority"     # Mercury écrase toujours
    PRESERVE_EXISTING = "preserve_existing"   # Garde l'existant si non vide
    SMART_MERGE = "smart_merge"              # Fusion intelligente


@dataclass
class MercuryResult:
    """Structure des résultats Mercury Parser"""
    title: Optional[str] = None
    content: Optional[str] = None
    markdown: Optional[str] = None
    lead_image_url: Optional[str] = None
    date_published: Optional[str] = None
    author: Optional[str] = None
    excerpt: Optional[str] = None
    domain: Optional[str] = None
    word_count: Optional[int] = None
    direction: Optional[str] = None
    total_pages: Optional[int] = None
    rendered_pages: Optional[int] = None
    next_page_url: Optional[str] = None
    media: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Optional[Dict] = None
    error: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None


@dataclass
class ExpressionUpdate:
    """Structure pour les mises à jour d'expression"""
    expression_id: int
    field_updates: Dict[str, Tuple[Any, Any]]  # (old_value, new_value)
    media_additions: List[Dict[str, Any]]
    link_additions: List[Dict[str, Any]]
    update_reason: str
    

class MercuryReadablePipeline:
    """Pipeline autonome pour l'extraction readable avec Mercury Parser"""
    
    def __init__(self, 
                 mercury_path: str = "mercury-parser",
                 merge_strategy: MergeStrategy = MergeStrategy.SMART_MERGE,
                 batch_size: int = 10,
                 max_retries: int = 3):
        self.mercury_path = mercury_path
        self.merge_strategy = merge_strategy
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    async def process_land(self, 
                          land: model.Land, 
                          limit: Optional[int] = None,
                          depth: Optional[int] = None) -> Dict[str, Any]:
        """
        Point d'entrée principal du pipeline
        
        Args:
            land: Land à traiter
            limit: Nombre maximum d'expressions à traiter
            depth: Profondeur maximale des expressions à traiter
        
        Returns:
            Statistiques du traitement
        """
        self.logger.info(f"Starting readable pipeline for land: {land.name}")
        
        # Récupération du dictionnaire du land pour le calcul de pertinence
        dictionary = get_land_dictionary(land)
        
        # Récupération des expressions à traiter
        expressions = self._get_expressions_to_process(land, limit, depth)
        
        # Traitement par batch
        total_expressions = len(expressions)
        for i in range(0, total_expressions, self.batch_size):
            batch = expressions[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_expressions + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches}")
            await self._process_batch(batch, dictionary)
        
        return self._get_pipeline_stats()
    
    def _get_expressions_to_process(self, 
                                   land: model.Land, 
                                   limit: Optional[int],
                                   depth: Optional[int]) -> List[model.Expression]:
        """Récupère les expressions à traiter selon les critères"""
        query = model.Expression.select().where(
            model.Expression.land == land
        )
        
        # Filtre par profondeur si spécifié
        if depth is not None:
            query = query.where(model.Expression.depth <= depth)
        
        # Ordre par priorité : d'abord celles jamais traitées, puis par date
        query = query.order_by(
            model.Expression.readable_at.asc(nulls='first'),
            model.Expression.depth.asc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return list(query)
    
    async def _process_batch(self, 
                           expressions: List[model.Expression],
                           dictionary) -> None:
        """Traite un batch d'expressions en parallèle"""
        tasks = []
        for expression in expressions:
            task = self._process_single_expression(expression, dictionary)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traitement des résultats
        for expression, result in zip(expressions, results):
            if isinstance(result, Exception):
                self.logger.error(f"Error processing {expression.url}: {result}")
                self.stats['errors'] += 1
            else:
                self.stats['processed'] += 1
    
    async def _process_single_expression(self,
                                       expression: model.Expression,
                                       dictionary) -> Optional[ExpressionUpdate]:
        """
        Traite une expression unique avec Mercury Parser
        """
        try:
            # Extraction avec Mercury Parser
            mercury_result = await self._extract_with_mercury(expression.url)
            
            if mercury_result.error:
                self.logger.warning(f"Mercury extraction failed for {expression.url}: {mercury_result.error}")
                return None
            
            # Préparation de la mise à jour
            update = self._prepare_expression_update(expression, mercury_result)
            
            if not update.field_updates and not update.media_additions and not update.link_additions:
                self.logger.debug(f"No updates needed for {expression.url}")
                self.stats['skipped'] += 1
                return None
            
            # Application des mises à jour
            self._apply_updates(expression, update, dictionary)
            self.stats['updated'] += 1
            
            return update
            
        except Exception as e:
            self.logger.error(f"Failed to process {expression.url}: {e}")
            raise
    
    async def _extract_with_mercury(self, url: str) -> MercuryResult:
        """
        Extraction avec Mercury Parser via subprocess
        """
        result = MercuryResult(extraction_timestamp=datetime.now())
        
        for attempt in range(self.max_retries):
            try:
                proc = await asyncio.create_subprocess_shell(
                    f'{self.mercury_path} "{url}" --format=markdown --extract-media --extract-links',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    result.error = error_msg
                    return result
                
                # Parse JSON response
                data = json.loads(stdout.decode())
                result.raw_response = data
                
                # Mapping des champs Mercury vers notre structure
                result.title = data.get('title')
                result.content = data.get('content')  # HTML content
                result.markdown = data.get('markdown', data.get('content'))  # Fallback to content
                result.lead_image_url = data.get('lead_image_url')
                result.date_published = data.get('date_published')
                result.author = data.get('author')
                result.excerpt = data.get('excerpt')
                result.domain = data.get('domain')
                result.word_count = data.get('word_count')
                result.direction = data.get('direction')
                result.total_pages = data.get('total_pages')
                result.rendered_pages = data.get('rendered_pages')
                result.next_page_url = data.get('next_page_url')
                
                # Extraction des médias et liens
                self._extract_media_and_links(data, result)
                
                return result
                
            except json.JSONDecodeError as e:
                result.error = f"Invalid JSON response: {e}"
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                result.error = str(e)
                return result
        
        return result
    
    def _extract_media_and_links(self, data: Dict, result: MercuryResult) -> None:
        """Extrait les médias et liens du résultat Mercury"""
        # Extraction des images
        if 'images' in data:
            for img in data.get('images', []):
                media_item = {
                    'type': 'image',
                    'url': img.get('src', img),
                    'alt': img.get('alt', '') if isinstance(img, dict) else '',
                    'title': img.get('title', '') if isinstance(img, dict) else ''
                }
                result.media.append(media_item)
        
        # Extraction des vidéos
        if 'videos' in data:
            for video in data.get('videos', []):
                media_item = {
                    'type': 'video',
                    'url': video.get('src', video),
                    'poster': video.get('poster', '') if isinstance(video, dict) else ''
                }
                result.media.append(media_item)
        
        # Extraction des liens
        if 'links' in data:
            for link in data.get('links', []):
                link_item = {
                    'url': link.get('href', link),
                    'text': link.get('text', '') if isinstance(link, dict) else '',
                    'title': link.get('title', '') if isinstance(link, dict) else ''
                }
                result.links.append(link_item)
    
    def _prepare_expression_update(self, 
                                 expression: model.Expression,
                                 mercury_result: MercuryResult) -> ExpressionUpdate:
        """
        Prépare les mises à jour en appliquant la stratégie de fusion
        """
        update = ExpressionUpdate(
            expression_id=expression.id,
            field_updates={},
            media_additions=[],
            link_additions=[],
            update_reason=f"Mercury extraction at {mercury_result.extraction_timestamp}"
        )
        
        # Mapping des champs à vérifier
        field_mapping = {
            'title': mercury_result.title,
            'description': mercury_result.excerpt,
            'readable': mercury_result.markdown,
            'lang': mercury_result.direction,  # Approximation
            'published_at': self._parse_date(mercury_result.date_published)
        }
        
        # Application de la stratégie de fusion pour chaque champ
        for field_name, mercury_value in field_mapping.items():
            if mercury_value is None:
                continue
                
            current_value = getattr(expression, field_name, None)
            new_value = self._apply_merge_strategy(current_value, mercury_value, field_name)
            
            if new_value != current_value:
                update.field_updates[field_name] = (current_value, new_value)
        
        # Gestion des médias
        update.media_additions = self._prepare_media_updates(expression, mercury_result)
        
        # Gestion des liens (pour ExpressionLink)
        update.link_additions = self._prepare_link_updates(expression, mercury_result)
        
        return update
    
    def _apply_merge_strategy(self, 
                            current_value: Any, 
                            mercury_value: Any,
                            field_name: str) -> Any:
        """
        Applique la stratégie de fusion configurée
        
        Logique:
        - Si base vide -> remplit avec Mercury
        - Si Mercury plein et base pleine -> selon stratégie
        - Si base pleine et Mercury vide -> garde base
        """
        # Si la base est vide, on prend Mercury
        if not current_value:
            return mercury_value
        
        # Si Mercury est vide, on garde la base
        if not mercury_value:
            return current_value
        
        # Les deux ont des valeurs, on applique la stratégie
        if self.merge_strategy == MergeStrategy.MERCURY_PRIORITY:
            return mercury_value
        elif self.merge_strategy == MergeStrategy.PRESERVE_EXISTING:
            return current_value
        elif self.merge_strategy == MergeStrategy.SMART_MERGE:
            return self._smart_merge(current_value, mercury_value, field_name)
        
        return current_value
    
    def _smart_merge(self, current_value: Any, mercury_value: Any, field_name: str) -> Any:
        """
        Fusion intelligente selon le type de champ
        """
        if field_name == 'title':
            # Préfère le titre le plus long et informatif
            if len(str(mercury_value)) > len(str(current_value)):
                return mercury_value
            return current_value
            
        elif field_name == 'readable':
            # Pour le contenu, préfère Mercury qui est généralement plus propre
            return mercury_value
            
        elif field_name == 'description':
            # Garde la description la plus longue
            if len(str(mercury_value)) > len(str(current_value)):
                return mercury_value
            return current_value
            
        else:
            # Par défaut, Mercury a priorité pour les autres champs
            return mercury_value
    
    def _prepare_media_updates(self, 
                             expression: model.Expression,
                             mercury_result: MercuryResult) -> List[Dict[str, Any]]:
        """Prépare les ajouts de médias"""
        # Récupère les médias existants
        existing_media_urls = set(
            media.url for media in 
            model.Media.select().where(model.Media.expression == expression)
        )
        
        # Nouveaux médias à ajouter
        new_media = []
        for media in mercury_result.media:
            if media['url'] not in existing_media_urls:
                # Résolution des URLs relatives
                media['url'] = self._resolve_url(media['url'], expression.url)
                new_media.append(media)
        
        return new_media
    
    def _prepare_link_updates(self,
                            expression: model.Expression,
                            mercury_result: MercuryResult) -> List[Dict[str, Any]]:
        """Prépare les ajouts de liens"""
        # Pour l'instant, on collecte juste les liens uniques
        # L'ajout réel se fera dans _apply_updates
        unique_links = []
        seen_urls = set()
        
        for link in mercury_result.links:
            url = self._resolve_url(link['url'], expression.url)
            if url not in seen_urls and self._is_valid_link(url):
                seen_urls.add(url)
                link['url'] = url
                unique_links.append(link)
        
        return unique_links
    
    def _apply_updates(self,
                      expression: model.Expression,
                      update: ExpressionUpdate,
                      dictionary) -> None:
        """
        Applique les mises à jour à la base de données
        """
        # Mise à jour des champs de l'expression
        for field_name, (old_value, new_value) in update.field_updates.items():
            setattr(expression, field_name, new_value)
            self.logger.debug(f"Updated {field_name}: {old_value} -> {new_value}")
        
        # Mise à jour du timestamp
        expression.readable_at = datetime.now()
        
        # Recalcul de la pertinence si le contenu a changé
        if 'readable' in update.field_updates:
            expression.relevance = self._calculate_relevance(dictionary, expression)
        
        # Sauvegarde de l'expression
        expression.save()
        
        # Ajout des nouveaux médias
        for media_data in update.media_additions:
            model.Media.create(
                expression=expression,
                url=media_data['url'],
                type=media_data['type']
            )
        
        # Ajout des nouveaux liens
        self._update_expression_links(expression, update.link_additions)
    
    def _update_expression_links(self, 
                               expression: model.Expression,
                               new_links: List[Dict[str, Any]]) -> None:
        """Met à jour les liens de l'expression"""
        # Suppression des anciens liens
        model.ExpressionLink.delete().where(
            model.ExpressionLink.source == expression
        ).execute()
        
        # Ajout des nouveaux liens
        for link_data in new_links:
            target_expression = self._get_or_create_expression(
                expression.land, 
                link_data['url'],
                expression.depth + 1
            )
            
            if target_expression:
                try:
                    model.ExpressionLink.create(
                        source=expression,
                        target=target_expression
                    )
                except:
                    pass  # Ignore les doublons
    
    def _calculate_relevance(self, dictionary, expression: model.Expression) -> int:
        """Calcule la pertinence selon le dictionnaire du land"""
        # Réutilise la logique existante de core.expression_relevance
        from .core import expression_relevance
        return expression_relevance(dictionary, expression)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse une date depuis Mercury"""
        if not date_str:
            return None
        
        try:
            # Essaye plusieurs formats courants
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%SZ']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """Résout une URL relative en URL absolue"""
        from urllib.parse import urljoin
        
        if not url:
            return ''
        
        if url.startswith(('http://', 'https://', 'data:')):
            return url
        
        return urljoin(base_url, url)
    
    def _is_valid_link(self, url: str) -> bool:
        """Vérifie si un lien est valide pour l'ajout"""
        from .core import is_crawlable
        return is_crawlable(url)
    
    def _get_or_create_expression(self, 
                                land: model.Land,
                                url: str,
                                depth: int) -> Optional[model.Expression]:
        """Récupère ou crée une expression"""
        from .core import add_expression
        return add_expression(land, url, depth)
    
    def _get_pipeline_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du pipeline"""
        return {
            'processed': self.stats['processed'],
            'updated': self.stats['updated'],
            'errors': self.stats['errors'],
            'skipped': self.stats['skipped'],
            'success_rate': (self.stats['updated'] / self.stats['processed'] * 100) 
                           if self.stats['processed'] > 0 else 0
        }


# Fonction helper pour l'intégration avec le CLI
async def run_readable_pipeline(land: model.Land,
                              limit: Optional[int] = None,
                              depth: Optional[int] = None,
                              merge_strategy: str = 'smart_merge') -> Tuple[int, int]:
    """
    Point d'entrée pour le contrôleur
    
    Returns:
        Tuple (processed_count, error_count)
    """
    strategy_map = {
        'mercury_priority': MergeStrategy.MERCURY_PRIORITY,
        'preserve_existing': MergeStrategy.PRESERVE_EXISTING,
        'smart_merge': MergeStrategy.SMART_MERGE
    }
    
    pipeline = MercuryReadablePipeline(
        merge_strategy=strategy_map.get(merge_strategy, MergeStrategy.SMART_MERGE)
    )
    
    stats = await pipeline.process_land(land, limit, depth)
    
    return stats['processed'], stats['errors']
```

## Modifications dans `mwi/controller.py`

```python
# Dans la classe LandController, remplacer la méthode readable

@staticmethod
def readable(args: core.Namespace):
    """
    Pipeline Mercury Parser pour l'extraction readable enrichie
    :param args:
    :return:
    """
    core.check_args(args, 'name')
    
    # Récupération des paramètres
    fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
    depth_limit = core.get_arg_option('depth', args, set_type=int, default=None)
    merge_strategy = core.get_arg_option('merge', args, set_type=str, default='smart_merge')
    
    if fetch_limit > 0:
        print(f'Fetch limit set to {fetch_limit} URLs')
    if depth_limit is not None:
        print(f'Depth limit set to {depth_limit}')
    print(f'Merge strategy: {merge_strategy}')
    
    land = model.Land.get_or_none(model.Land.name == args.name)
    if land is None:
        print('Land "%s" not found' % args.name)
        return 0
    
    # Import du nouveau pipeline
    from .readable_pipeline import run_readable_pipeline
    
    # Configuration de l'event loop selon la plateforme
    if sys.platform == 'win32':
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        run_readable_pipeline(land, fetch_limit, depth_limit, merge_strategy)
    )
    
    print("%d expressions processed (%d errors)" % results)
    return 1
```

## Modifications dans `mwi/cli.py`

```python
# Ajouter les nouveaux arguments dans command_input()

parser.add_argument('--depth',
                    type=int,
                    help='Set maximum depth for readable extraction',
                    nargs='?')
parser.add_argument('--merge',
                    type=str,
                    help='Merge strategy: mercury_priority, preserve_existing, smart_merge',
                    nargs='?',
                    default='smart_merge')
```

## Configuration et installation

### 1. Installation/vérification de Mercury Parser

```bash
# Vérifier si Mercury Parser est installé
mercury-parser --version

# Si non installé
npm install -g @postlight/mercury-parser

# Ou avec yarn
yarn global add @postlight/mercury-parser
```

### 2. Configuration système

```python
# Dans settings.py, ajouter:

# Mercury Parser settings
mercury_parser = {
    'binary_path': 'mercury-parser',  # ou chemin complet
    'timeout': 30,
    'batch_size': 10,
    'max_retries': 3,
    'default_merge_strategy': 'smart_merge'
}
```

## Tests unitaires

```python
# tests/test_readable_pipeline.py

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mwi.readable_pipeline import MercuryReadablePipeline, MercuryResult, MergeStrategy

class TestMercuryReadablePipeline:
    
    @pytest.fixture
    def pipeline(self):
        return MercuryReadablePipeline(merge_strategy=MergeStrategy.SMART_MERGE)
    
    @pytest.fixture
    def mock_expression(self):
        expression = Mock()
        expression.id = 1
        expression.url = "https://example.com/article"
        expression.title = "Old Title"
        expression.readable = None
        expression.depth = 1
        return expression
    
    @pytest.mark.asyncio
    async def test_mercury_extraction_success(self, pipeline):
        """Test extraction réussie avec Mercury"""
        mock_response = {
            "title": "New Article Title",
            "content": "<p>Article content</p>",
            "markdown": "Article content in markdown",
            "lead_image_url": "https://example.com/image.jpg",
            "author": "John Doe",
            "date_published": "2024-01-15T10:00:00Z",
            "images": [{"src": "https://example.com/img1.jpg", "alt": "Image 1"}],
            "links": [{"href": "/page2", "text": "Next page"}]
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (
                json.dumps(mock_response).encode(),
                b''
            )
            mock_subprocess.return_value = mock_proc
            
            result = await pipeline._extract_with_mercury("https://example.com/article")
            
            assert result.title == "New Article Title"
            assert result.markdown == "Article content in markdown"
            assert len(result.media) == 1
            assert result.media[0]['url'] == "https://example.com/img1.jpg"
            assert len(result.links) == 1
    
    def test_merge_strategy_smart(self, pipeline):
        """Test stratégie de fusion intelligente"""
        # Test pour le titre - préfère le plus long
        merged = pipeline._smart_merge("Short", "Much Longer Title", "title")
        assert merged == "Much Longer Title"
        
        # Test pour readable - Mercury a priorité
        merged = pipeline._smart_merge("Old content", "New content", "readable")
        assert merged == "New content"
    
    def test_merge_strategy_preserve_existing(self):
        """Test stratégie de préservation"""
        pipeline = MercuryReadablePipeline(merge_strategy=MergeStrategy.PRESERVE_EXISTING)
        
        result = pipeline._apply_merge_strategy("Existing", "New", "title")
        assert result == "Existing"
        
        # Mais remplit si vide
        result = pipeline._apply_merge_strategy(None, "New", "title")
        assert result == "New"
```

## Commandes d'utilisation

```bash
# Extraction basique
python mywi.py land readable --name="MyResearchTopic"

# Avec limite et profondeur
python mywi.py land readable --name="MyResearchTopic" --limit=100 --depth=2

# Avec stratégie de fusion spécifique
python mywi.py land readable --name="MyResearchTopic" --merge=mercury_priority

# Stratégies disponibles:
# - smart_merge (défaut): Fusion intelligente selon le type de champ
# - mercury_priority: Mercury écrase toujours les données existantes
# - preserve_existing: Garde les données existantes si non vides
```

## Points clés du pipeline

### 1. **Autonomie complète**
- Module séparé `readable_pipeline.py`
- Aucune dépendance aux autres extracteurs
- Configuration indépendante

### 2. **Logique de fusion bidirectionnelle**
- Si base vide → remplit avec Mercury
- Si Mercury plein → selon stratégie (smart, priority, preserve)
- Si Mercury vide et base pleine → garde la base

### 3. **Extraction enrichie**
- Markdown avec préservation des liens
- Extraction des médias (images, vidéos)
- Métadonnées complètes (auteur, date, etc.)

### 4. **Robustesse**
- Retry avec exponential backoff
- Gestion d'erreurs granulaire
- Logging détaillé
- Statistiques de traitement

### 5. **Performance**
- Traitement par batch asynchrone
- Parallélisation des extractions
- Cache potentiel (à implémenter si besoin)

Ce pipeline autonome garantit une extraction de qualité tout en préservant l'intégrité des données existantes selon une logique de fusion configurable.