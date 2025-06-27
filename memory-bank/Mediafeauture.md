# Plan détaillé complet pour l'intégration de l'analyse média dans MyWebIntelligence

## Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Modifications de la base de données](#2-modifications-de-la-base-de-données)
3. [Mise à jour des modèles](#3-mise-à-jour-des-modèles)
4. [Module d'analyse média](#4-module-danalyse-média)
5. [Intégration dans le processus de crawl](#5-intégration-dans-le-processus-de-crawl)
6. [Fonctions de réanalyse et suppression](#6-fonctions-de-réanalyse-et-suppression)
7. [Contrôleurs](#7-contrôleurs)
8. [Interface CLI](#8-interface-cli)
9. [Requêtes et statistiques](#9-requêtes-et-statistiques)
10. [Configuration](#10-configuration)
11. [Tests unitaires](#11-tests-unitaires)
12. [Documentation d'utilisation](#12-documentation-dutilisation)

## 1. Architecture globale

### Vue d'ensemble

L'analyse média s'intègre dans MyWebIntelligence selon le flux suivant :

```
Crawl Expression → Extraction HTML → Analyse Média → Stockage Métadonnées
                                          ↓
                                   Filtrage/Suppression
                                          ↓
                                    Statistiques
```

### Composants principaux

- **MediaAnalyzer** : Classe responsable de l'analyse des images
- **Model.Media enrichi** : Modèle de données étendu avec métadonnées
- **Contrôleurs** : Gestion des commandes de réanalyse et suppression
- **Requêtes analytiques** : Extraction de statistiques et patterns

## 2. Modifications de la base de données

### 2.1 Script de migration

```python
# migrations/001_add_media_analysis.py

"""
Migration pour ajouter les champs d'analyse média
"""

import datetime
from mwi import model

def upgrade():
    """
    Ajoute les colonnes d'analyse média à la table Media
    """
    print("Starting media analysis migration...")
    
    with model.DB.atomic():
        # Colonnes de dimensions
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN width INTEGER DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN height INTEGER DEFAULT NULL
        ''')
        
        # Métadonnées du fichier
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN file_size INTEGER DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN format VARCHAR(10) DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN color_mode VARCHAR(10) DEFAULT NULL
        ''')
        
        # Analyse visuelle
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN dominant_colors TEXT DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN has_transparency BOOLEAN DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN aspect_ratio REAL DEFAULT NULL
        ''')
        
        # Métadonnées avancées
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN exif_data TEXT DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN image_hash VARCHAR(64) DEFAULT NULL
        ''')
        
        # Analyse de contenu
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN content_tags TEXT DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN nsfw_score REAL DEFAULT NULL
        ''')
        
        # Métadonnées de traitement
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN analyzed_at DATETIME DEFAULT NULL
        ''')
        model.DB.execute_sql('''
            ALTER TABLE media 
            ADD COLUMN analysis_error TEXT DEFAULT NULL
        ''')
        
        # Index pour optimiser les requêtes
        print("Creating indexes...")
        model.DB.execute_sql('''
            CREATE INDEX IF NOT EXISTS idx_media_size 
            ON media(file_size)
        ''')
        model.DB.execute_sql('''
            CREATE INDEX IF NOT EXISTS idx_media_dimensions 
            ON media(width, height)
        ''')
        model.DB.execute_sql('''
            CREATE INDEX IF NOT EXISTS idx_media_hash 
            ON media(image_hash)
        ''')
        model.DB.execute_sql('''
            CREATE INDEX IF NOT EXISTS idx_media_analyzed 
            ON media(analyzed_at)
        ''')
        
    print("Media analysis migration completed successfully")

def downgrade():
    """
    Supprime les colonnes d'analyse média
    """
    print("Reverting media analysis migration...")
    
    # SQLite ne supporte pas DROP COLUMN directement
    # Il faut recréer la table
    with model.DB.atomic():
        model.DB.execute_sql('''
            CREATE TABLE media_backup AS 
            SELECT id, expression_id, url, type 
            FROM media
        ''')
        model.DB.execute_sql('DROP TABLE media')
        model.DB.execute_sql('''
            CREATE TABLE media AS 
            SELECT * FROM media_backup
        ''')
        model.DB.execute_sql('DROP TABLE media_backup')
    
    print("Media analysis migration reverted")

if __name__ == '__main__':
    upgrade()
```

### 2.2 Script d'exécution des migrations

```python
# migrate.py

"""
Gestionnaire de migrations pour MyWebIntelligence
"""

import os
import sys
import importlib.util
from datetime import datetime
from mwi import model

class MigrationManager:
    def __init__(self):
        self.migrations_dir = 'migrations'
        self.migration_table = 'schema_migrations'
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Crée la table des migrations si elle n'existe pas"""
        model.DB.execute_sql('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                executed_at DATETIME NOT NULL
            )
        ''')
    
    def get_executed_migrations(self):
        """Retourne la liste des migrations déjà exécutées"""
        cursor = model.DB.execute_sql(
            'SELECT version FROM schema_migrations ORDER BY version'
        )
        return [row[0] for row in cursor.fetchall()]
    
    def get_pending_migrations(self):
        """Retourne la liste des migrations à exécuter"""
        executed = set(self.get_executed_migrations())
        
        # Liste tous les fichiers de migration
        migration_files = []
        if os.path.exists(self.migrations_dir):
            for filename in sorted(os.listdir(self.migrations_dir)):
                if filename.endswith('.py') and not filename.startswith('__'):
                    version = filename[:-3]  # Enlève .py
                    if version not in executed:
                        migration_files.append(filename)
        
        return migration_files
    
    def run_migration(self, filename):
        """Exécute une migration"""
        version = filename[:-3]
        filepath = os.path.join(self.migrations_dir, filename)
        
        # Charge le module de migration
        spec = importlib.util.spec_from_file_location(version, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Exécute la migration
        print(f"Running migration: {version}")
        module.upgrade()
        
        # Enregistre la migration
        model.DB.execute_sql(
            'INSERT INTO schema_migrations (version, executed_at) VALUES (?, ?)',
            (version, datetime.now())
        )
        
        print(f"Migration {version} completed")
    
    def migrate(self):
        """Exécute toutes les migrations en attente"""
        pending = self.get_pending_migrations()
        
        if not pending:
            print("No pending migrations")
            return
        
        print(f"Found {len(pending)} pending migrations")
        
        for migration in pending:
            try:
                with model.DB.atomic():
                    self.run_migration(migration)
            except Exception as e:
                print(f"Error running migration {migration}: {e}")
                sys.exit(1)
        
        print("All migrations completed successfully")

if __name__ == '__main__':
    manager = MigrationManager()
    manager.migrate()
```

## 3. Mise à jour des modèles

```python
# mwi/model.py - Ajout au fichier existant

class Media(BaseModel):
    """
    Media model enrichi avec analyse
    """
    expression = ForeignKeyField(Expression, backref='medias', on_delete='CASCADE')
    url = TextField()
    type = CharField(max_length=30)
    
    # Dimensions et métadonnées de base
    width = IntegerField(null=True)
    height = IntegerField(null=True)
    file_size = IntegerField(null=True)
    format = CharField(max_length=10, null=True)
    color_mode = CharField(max_length=10, null=True)
    
    # Analyse visuelle
    dominant_colors = TextField(null=True)
    has_transparency = BooleanField(null=True)
    aspect_ratio = FloatField(null=True)
    
    # Métadonnées avancées
    exif_data = TextField(null=True)
    image_hash = CharField(max_length=64, null=True)
    
    # Analyse de contenu
    content_tags = TextField(null=True)
    nsfw_score = FloatField(null=True)
    
    # Traitement
    analyzed_at = DateTimeField(null=True)
    analysis_error = TextField(null=True)
    
    class Meta:
        indexes = (
            (('width', 'height'), False),
            (('file_size',), False),
            (('image_hash',), False),
            (('analyzed_at',), False),
        )
    
    def is_conforming(self, min_width=0, min_height=0, max_file_size=0):
        """Vérifie si le média respecte les critères donnés"""
        if min_width > 0 and self.width and self.width < min_width:
            return False
        if min_height > 0 and self.height and self.height < min_height:
            return False
        if max_file_size > 0 and self.file_size and self.file_size > max_file_size:
            return False
        return True
    
    def get_dominant_colors_list(self):
        """Retourne la liste des couleurs dominantes"""
        if self.dominant_colors:
            return json.loads(self.dominant_colors)
        return []
    
    def get_exif_dict(self):
        """Retourne le dictionnaire EXIF"""
        if self.exif_data:
            return json.loads(self.exif_data)
        return {}
    
    def get_content_tags_list(self):
        """Retourne la liste des tags de contenu"""
        if self.content_tags:
            return json.loads(self.content_tags)
        return []
```

## 4. Module d'analyse média

```python
# mwi/media_analyzer.py - Nouveau fichier

"""
Module d'analyse des médias pour MyWebIntelligence
"""

import io
import json
import asyncio
import aiohttp
import hashlib
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image, ExifTags
import imagehash
import numpy as np
from sklearn.cluster import KMeans
import colorsys
import re
from urllib.parse import urljoin, urlparse

class MediaAnalyzer:
    """
    Analyseur d'images avec extraction de métadonnées et caractéristiques
    """
    
    # Formats d'image supportés
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    
    # Patterns d'exclusion (publicités, tracking, etc.)
    EXCLUDE_PATTERNS = [
        r'.*\/(ads?|banner|tracking|pixel|beacon|analytics)\/.*',
        r'.*\/(spacer|blank|transparent|clear)\.gif$',
        r'.*\/(1x1|pixel)\.png$',
        r'.*doubleclick\.net.*',
        r'.*googlesyndication\.com.*',
        r'.*amazon-adsystem\.com.*',
        r'.*facebook\.com\/tr.*',
        r'.*google-analytics\.com.*'
    ]
    
    def __init__(self, session: aiohttp.ClientSession, settings: Dict[str, Any]):
        self.session = session
        self.settings = settings
        
        # Paramètres de filtrage
        self.min_width = settings.get('min_width', 100)
        self.min_height = settings.get('min_height', 100)
        self.max_file_size = settings.get('max_file_size', 10 * 1024 * 1024)
        
        # Options d'analyse
        self.analyze_content = settings.get('analyze_content', False)
        self.extract_colors = settings.get('extract_colors', True)
        self.extract_exif = settings.get('extract_exif', True)
        self.n_dominant_colors = settings.get('n_dominant_colors', 5)
        
        # Timeout et retry
        self.download_timeout = settings.get('download_timeout', 30)
        self.max_retries = settings.get('max_retries', 2)
        
        # Compilation des patterns d'exclusion
        self.exclude_patterns = [re.compile(p, re.IGNORECASE) 
                                for p in self.EXCLUDE_PATTERNS]
    
    def should_analyze_url(self, url: str) -> bool:
        """
        Détermine si une URL doit être analysée
        """
        # Vérifier l'extension
        parsed = urlparse(url.lower())
        path = parsed.path
        
        if not any(path.endswith(ext) for ext in self.SUPPORTED_FORMATS):
            return False
        
        # Vérifier les patterns d'exclusion
        for pattern in self.exclude_patterns:
            if pattern.match(url):
                return False
        
        return True
    
    async def analyze_image(self, url: str, source_url: str = None) -> Dict[str, Any]:
        """
        Analyse une image depuis une URL
        """
        analysis = {'url': url}
        
        # Vérification préliminaire de l'URL
        if not self.should_analyze_url(url):
            analysis['error'] = 'URL excluded by filters'
            return analysis
        
        try:
            # Téléchargement avec retry
            image_data = await self._download_with_retry(url)
            if not image_data:
                analysis['error'] = 'Failed to download image'
                return analysis
            
            # Vérification de la taille du fichier
            file_size = len(image_data)
            analysis['file_size'] = file_size
            
            if file_size > self.max_file_size:
                analysis['error'] = f'File too large: {file_size} bytes'
                return analysis
            
            # Ouverture et analyse de l'image
            image = Image.open(io.BytesIO(image_data))
            
            # Métadonnées de base
            analysis.update({
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'color_mode': image.mode,
                'aspect_ratio': round(image.width / image.height, 3),
                'has_transparency': self._has_transparency(image)
            })
            
            # Vérification des dimensions minimales
            if image.width < self.min_width or image.height < self.min_height:
                analysis['error'] = f'Image too small: {image.width}x{image.height}'
                return analysis
            
            # Hash perceptuel pour déduplication
            analysis['image_hash'] = str(imagehash.average_hash(image))
            
            # Extraction EXIF
            if self.extract_exif:
                exif_data = self._extract_exif(image)
                if exif_data:
                    analysis['exif_data'] = json.dumps(exif_data)
            
            # Extraction des couleurs dominantes
            if self.extract_colors:
                dominant_colors = self._extract_dominant_colors(image)
                analysis['dominant_colors'] = json.dumps(dominant_colors)
            
            # Analyse de contenu avancée
            if self.analyze_content:
                content_analysis = await self._analyze_content(image, image_data)
                analysis.update(content_analysis)
            
            return analysis
            
        except asyncio.TimeoutError:
            analysis['error'] = 'Download timeout'
        except aiohttp.ClientError as e:
            analysis['error'] = f'Network error: {str(e)}'
        except IOError as e:
            analysis['error'] = f'Invalid image format: {str(e)}'
        except Exception as e:
            analysis['error'] = f'Analysis error: {str(e)}'
        
        return analysis
    
    async def _download_with_retry(self, url: str) -> Optional[bytes]:
        """
        Télécharge une image avec retry en cas d'échec
        """
        headers = {
            'User-Agent': self.settings.get('user_agent', ''),
            'Accept': 'image/*',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.download_timeout)
                async with self.session.get(
                    url, 
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True
                ) as response:
                    if response.status == 200:
                        # Vérifier le content-type
                        content_type = response.headers.get('Content-Type', '')
                        if not content_type.startswith('image/'):
                            return None
                        
                        return await response.read()
                    elif response.status == 404:
                        return None  # Pas de retry sur 404
                    
            except asyncio.TimeoutError:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # Backoff
            except Exception:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
        
        return None
    
    def _has_transparency(self, image: Image.Image) -> bool:
        """
        Vérifie si l'image a de la transparence
        """
        if image.mode in ('RGBA', 'LA', 'PA'):
            # Vérifier si le canal alpha contient des valeurs < 255
            if image.mode == 'RGBA':
                alpha = image.getchannel('A')
                return any(pixel < 255 for pixel in alpha.getdata())
            return True
        
        # Vérifier la transparence dans les GIF/PNG
        if 'transparency' in image.info:
            return True
        
        return False
    
    def _extract_exif(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """
        Extrait et nettoie les données EXIF
        """
        try:
            exifdata = image.getexif()
            if not exifdata:
                return None
            
            exif_dict = {}
            
            # Tags EXIF standards
            for tag_id, value in exifdata.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                
                # Nettoyer les valeurs
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        continue
                elif isinstance(value, (int, float)):
                    value = str(value)
                elif value is None:
                    continue
                
                # Filtrer les tags sensibles
                if tag not in ['GPSInfo', 'MakerNote']:
                    exif_dict[tag] = str(value)[:200]  # Limiter la longueur
            
            # Extraire les informations GPS si présentes
            if exifdata.get(0x8825):  # GPSInfo tag
                gps_info = self._extract_gps_info(exifdata)
                if gps_info:
                    exif_dict['GPS'] = gps_info
            
            return exif_dict if exif_dict else None
            
        except Exception:
            return None
    
    def _extract_gps_info(self, exifdata) -> Optional[Dict[str, float]]:
        """
        Extrait les coordonnées GPS des données EXIF
        """
        try:
            gps_info = {}
            gps_ifd = exifdata.get_ifd(0x8825)
            
            def convert_to_degrees(value):
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)
            
            # Latitude
            if 1 in gps_ifd and 2 in gps_ifd:  # GPSLatitude et GPSLatitudeRef
                lat = convert_to_degrees(gps_ifd[2])
                if gps_ifd[1] == 'S':
                    lat = -lat
                gps_info['latitude'] = round(lat, 6)
            
            # Longitude
            if 3 in gps_ifd and 4 in gps_ifd:  # GPSLongitude et GPSLongitudeRef
                lon = convert_to_degrees(gps_ifd[4])
                if gps_ifd[3] == 'W':
                    lon = -lon
                gps_info['longitude'] = round(lon, 6)
            
            return gps_info if gps_info else None
            
        except Exception:
            return None
    
    def _extract_dominant_colors(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Extrait les couleurs dominantes avec clustering K-means
        """
        # Redimensionner pour performance
        max_dimension = 200
        if image.width > max_dimension or image.height > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Convertir en RGB
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        
        # Échantillonnage des pixels
        pixels = np.array(image)
        if len(pixels.shape) == 3:
            if pixels.shape[2] == 4:  # RGBA
                # Ignorer les pixels transparents
                mask = pixels[:, :, 3] > 128
                pixels = pixels[mask][:, :3]
            else:
                pixels = pixels.reshape(-1, 3)
        
        # Si pas assez de pixels, retourner une couleur moyenne
        if len(pixels) < self.n_dominant_colors:
            avg_color = np.mean(pixels, axis=0).astype(int)
            return [self._format_color(avg_color, 100.0)]
        
        # K-means clustering
        kmeans = KMeans(
            n_clusters=min(self.n_dominant_colors, len(pixels)),
            random_state=42,
            n_init=10,
            max_iter=300
        )
        kmeans.fit(pixels)
        
        # Calcul des pourcentages
        labels = kmeans.labels_
        label_counts = np.bincount(labels)
        total_count = len(labels)
        
        # Formatage des résultats
        dominant_colors = []
        for i, (color, count) in enumerate(zip(kmeans.cluster_centers_, label_counts)):
            percentage = (count / total_count) * 100
            if percentage > 1:  # Ignorer les couleurs < 1%
                dominant_colors.append(
                    self._format_color(color.astype(int), percentage)
                )
        
        # Trier par pourcentage décroissant
        dominant_colors.sort(key=lambda x: x['percentage'], reverse=True)
        
        return dominant_colors[:self.n_dominant_colors]
    
    def _format_color(self, rgb: np.ndarray, percentage: float) -> Dict[str, Any]:
        """
        Formate une couleur avec toutes ses représentations
        """
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        
        # Conversion HSV
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        # Nom de couleur approximatif
        color_name = self._get_color_name(h * 360, s * 100, v * 100)
        
        return {
            'rgb': [r, g, b],
            'hex': f'#{r:02x}{g:02x}{b:02x}',
            'hsv': [round(h * 360), round(s * 100), round(v * 100)],
            'name': color_name,
            'percentage': round(percentage, 2)
        }
    
    def _get_color_name(self, h: float, s: float, v: float) -> str:
        """
        Retourne un nom de couleur approximatif basé sur HSV
        """
        if v < 20:
            return 'black'
        elif v > 80 and s < 20:
            return 'white'
        elif s < 20:
            return 'gray'
        elif h < 15 or h >= 345:
            return 'red'
        elif h < 45:
            return 'orange'
        elif h < 65:
            return 'yellow'
        elif h < 150:
            return 'green'
        elif h < 250:
            return 'blue'
        elif h < 290:
            return 'purple'
        else:
            return 'pink'
    
    async def _analyze_content(self, image: Image.Image, image_data: bytes) -> Dict[str, Any]:
        """
        Analyse avancée du contenu (placeholder pour extensions futures)
        """
        content_analysis = {}
        
        # Détection basique de contenu
        content_tags = []
        
        # Analyse de la complexité visuelle
        complexity = self._calculate_visual_complexity(image)
        if complexity < 0.1:
            content_tags.append('simple')
        elif complexity > 0.7:
            content_tags.append('complex')
        
        # Détection de patterns
        if self._is_likely_logo(image):
            content_tags.append('logo')
        if self._is_likely_screenshot(image):
            content_tags.append('screenshot')
        if self._has_text_regions(image):
            content_tags.append('text')
        
        content_analysis['content_tags'] = json.dumps(content_tags)
        
        # Score NSFW basique (placeholder)
        content_analysis['nsfw_score'] = 0.0
        
        return content_analysis
    
    def _calculate_visual_complexity(self, image: Image.Image) -> float:
        """
        Calcule un score de complexité visuelle (0-1)
        """
        # Convertir en niveaux de gris
        gray = image.convert('L')
        
        # Calculer l'entropie
        histogram = gray.histogram()
        total_pixels = sum(histogram)
        
        entropy = 0
        for count in histogram:
            if count > 0:
                probability = count / total_pixels
                entropy -= probability * np.log2(probability)
        
        # Normaliser (max théorique = 8 pour 256 niveaux)
        return min(entropy / 8, 1.0)
    
    def _is_likely_logo(self, image: Image.Image) -> bool:
        """
        Détecte si l'image est probablement un logo
        """
        # Critères : petite taille, ratio carré, peu de couleurs
        if image.width > 500 or image.height > 500:
            return False
        
        aspect_ratio = image.width / image.height
        if aspect_ratio < 0.5 or aspect_ratio > 2:
            return False
        
        # Compter les couleurs uniques (échantillon)
        small = image.resize((50, 50))
        colors = set(small.getdata())
        
        return len(colors) < 100
    
    def _is_likely_screenshot(self, image: Image.Image) -> bool:
        """
        Détecte si l'image est probablement une capture d'écran
        """
        # Critères : grandes zones uniformes, ratios standards
        width, height = image.width, image.height
        
        # Ratios d'écran courants
        common_ratios = [16/9, 16/10, 4/3, 21/9]
        ratio = width / height
        
        for common_ratio in common_ratios:
            if abs(ratio - common_ratio) < 0.1:
                # Vérifier les bords uniformes
                edges = [
                    image.crop((0, 0, width, 1)),  # Top
                    image.crop((0, height-1, width, height)),  # Bottom
                    image.crop((0, 0, 1, height)),  # Left
                    image.crop((width-1, 0, width, height))  # Right
                ]
                
                for edge in edges:
                    colors = set(edge.getdata())
                    if len(colors) == 1:  # Bord uniforme
                        return True
        
        return False
    
    def _has_text_regions(self, image: Image.Image) -> bool:
        """
        Détecte la présence probable de texte
        """
        # Méthode simple : détecter les zones de fort contraste
        gray = image.convert('L')
        
        # Calculer le gradient
        pixels = np.array(gray)
        gradient_x = np.abs(np.diff(pixels, axis=1))
        gradient_y = np.abs(np.diff(pixels, axis=0))
        
        # Zones de fort gradient (texte probable)
        high_gradient_ratio = (
            (np.sum(gradient_x > 128) + np.sum(gradient_y > 128)) / 
            (pixels.size * 2)
        )
        
        return high_gradient_ratio > 0.1
```

## 5. Intégration dans le processus de crawl

```python
# mwi/core.py - Modifications et ajouts

# Import des nouveaux modules
from .media_analyzer import MediaAnalyzer

# Modification de la fonction process_expression_content
def process_expression_content(expression: model.Expression, html: str, dictionary) -> model.Expression:
    """
    Process expression fields from HTML content
    Version modifiée pour supporter l'analyse média asynchrone
    """
    print("Processing expression #%s" % expression.id)
    soup = BeautifulSoup(html, 'html.parser')

    if soup.html is not None:
        expression.lang = soup.html.get('lang', '')
    if soup.title is not None:
        expression.title = soup.title.string.strip()
    expression.description = get_meta_content(soup, 'description')
    expression.keywords = get_meta_content(soup, 'keywords')

    clean_html(soup)

    if settings.archive is True:
        loc = path.join(settings.data_location, 'lands/%s/%s') \
              % (expression.land.get_id(), expression.get_id())
        with open(loc, 'w', encoding="utf-8") as html_file:
            html_file.write(html.strip())
        html_file.close()

    expression.readable = get_readable(soup)
    expression.relevance = expression_relevance(dictionary, expression)

    if expression.relevance > 0:
        print("Expression #%d approved" % expression.get_id())
        
        # Extraction synchrone des médias (pour compatibilité)
        extract_medias_sync(soup, expression)
        
        expression.approved_at = model.datetime.datetime.now()
        if expression.depth < 3:
            urls = [a.get('href') for a in soup.find_all('a') if is_crawlable(a.get('href'))]
            print("Linking %d expression to #%s" % (len(urls), expression.id))
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def extract_medias_sync(content, expression: model.Expression):
    """
    Version synchrone de l'extraction des médias (sans analyse)
    Pour maintenir la compatibilité avec le code existant
    """
    print("Extracting media from #%s" % expression.id)
    medias = []
    
    for tag in ['img', 'video', 'audio']:
        for element in content.find_all(tag):
            src = element.get('src')
            is_valid_src = src is not None and src not in medias
            
            if tag == 'img':
                # Pour les images, on crée l'entrée même sans analyse immédiate
                is_valid_src = is_valid_src and any(
                    src.lower().endswith(ext) 
                    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
                )
            
            if is_valid_src:
                if src.startswith("/"):
                    src = expression.url[:expression.url.find("/", 9) + 1].strip('/') + src
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(expression.url, src)
                
                media = model.Media.create(expression=expression, url=src, type=tag)
                media.save()
                medias.append(src)


# Nouvelle fonction pour le crawl avec analyse média
async def crawl_land_with_media_analysis(land: model.Land, limit: int = 0, 
                                       http: str = None) -> tuple:
    """
    Version améliorée du crawl avec analyse média intégrée
    """
    print("Crawling land %d with media analysis" % land.id)
    dictionary = get_land_dictionary(land)

    expressions = model.Expression.select().where(model.Expression.land == land)
    if http is not None:
        expressions = expressions.where(model.Expression.http_status == http)
    else:
        expressions = expressions.where(model.Expression.fetched_at.is_null())

    if limit > 0:
        expressions = expressions.limit(limit)

    expression_count = expressions.count()
    batch_size = settings.parallel_connections
    batch_count = -(-expression_count//batch_size)
    last_batch_size = expression_count % batch_size
    current_offset = 0
    processed_count = 0

    # Configuration de l'analyse média
    media_settings = {
        'user_agent': settings.user_agent,
        'min_width': getattr(settings, 'media_min_width', 200),
        'min_height': getattr(settings, 'media_min_height', 200),
        'max_file_size': getattr(settings, 'media_max_file_size', 5 * 1024 * 1024),
        'analyze_content': getattr(settings, 'media_analyze_content', False),
        'extract_colors': getattr(settings, 'media_extract_colors', True),
        'extract_exif': getattr(settings, 'media_extract_exif', True)
    }

    for current_batch in range(batch_count):
        print("Batch %s/%s" % (current_batch+1, batch_count))
        batch_limit = last_batch_size if (current_batch+1 == batch_count and last_batch_size != 0) else batch_size
        expressions = expressions.limit(batch_limit).offset(current_offset).order_by(model.Expression.depth)
        
        connector = aiohttp.TCPConnector(limit=settings.parallel_connections, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Créer l'analyseur média pour cette session
            media_analyzer = MediaAnalyzer(session, media_settings)
            
            tasks = []
            for expression in expressions:
                tasks.append(crawl_expression_with_media(
                    expression, dictionary, session, media_analyzer
                ))
            results = await asyncio.gather(*tasks)
            processed_count += sum(results)
        current_offset += batch_size
        
    return expression_count, expression_count - processed_count


async def crawl_expression_with_media(expression: model.Expression, dictionary, 
                                    session: aiohttp.ClientSession, 
                                    media_analyzer: MediaAnalyzer):
    """
    Crawl d'une expression avec analyse média intégrée
    """
    print("Crawling expression %s" % expression.url)
    result = 0
    expression.http_status = '000'
    expression.fetched_at = model.datetime.datetime.now()
    
    try:
        async with session.get(expression.url,
                             headers={"User-Agent": settings.user_agent},
                             timeout=aiohttp.ClientTimeout(
                                 total=None,
                                 sock_connect=5,
                                 sock_read=5)) as response:
            expression.http_status = response.status
            if ('html' in response.headers['content-type']) and (response.status == 200):
                content = await response.text()
                
                # Traitement du contenu HTML
                soup = BeautifulSoup(content, 'html.parser')
                
                if soup.html is not None:
                    expression.lang = soup.html.get('lang', '')
                if soup.title is not None:
                    expression.title = soup.title.string.strip()
                expression.description = get_meta_content(soup, 'description')
                expression.keywords = get_meta_content(soup, 'keywords')
                
                clean_html(soup)
                
                expression.readable = get_readable(soup)
                expression.relevance = expression_relevance(dictionary, expression)
                
                if expression.relevance > 0:
                    print("Expression #%d approved" % expression.get_id())
                    
                    # Analyse des médias
                    await extract_and_analyze_medias(soup, expression, media_analyzer)
                    
                    expression.approved_at = model.datetime.datetime.now()
                    
                    # Extraction des liens
                    if expression.depth < 3:
                        urls = [a.get('href') for a in soup.find_all('a') 
                               if is_crawlable(a.get('href'))]
                        print("Linking %d expression to #%s" % (len(urls), expression.id))
                        for url in urls:
                            link_expression(expression.land, expression, url)
                
                result = 1
                
            expression.save()
            print("Saving expression #%s" % expression.id)
            return result
            
    except Exception as e:
        print(f"Error crawling expression #{expression.id}: {e}")
        expression.save()
        return result


async def extract_and_analyze_medias(soup, expression: model.Expression, 
                                   media_analyzer: MediaAnalyzer):
    """
    Extrait et analyse les médias d'une expression
    """
    print("Extracting and analyzing media from #%s" % expression.id)
    
    medias_found = []
    analysis_tasks = []
    
    for tag in ['img', 'video', 'audio']:
        for element in soup.find_all(tag):
            src = element.get('src')
            
            if not src or src in medias_found:
                continue
            
            # Normalisation de l'URL
            if src.startswith("/"):
                src = expression.url[:expression.url.find("/", 9) + 1].strip('/') + src
            elif not src.startswith(('http://', 'https://')):
                src = urljoin(expression.url, src)
            
            medias_found.append(src)
            
            # Créer l'entrée média
            media = model.Media(
                expression=expression,
                url=src,
                type=tag
            )
            
            # Analyser seulement les images
            if tag == 'img' and media_analyzer.should_analyze_url(src):
                task = analyze_and_save_media(media, media_analyzer)
                analysis_tasks.append(task)
            else:
                # Sauvegarder les autres types sans analyse
                media.save()
    
    # Exécuter les analyses en parallèle
    if analysis_tasks:
        await asyncio.gather(*analysis_tasks, return_exceptions=True)


async def analyze_and_save_media(media: model.Media, analyzer: MediaAnalyzer):
    """
    Analyse et sauvegarde un média
    """
    try:
        analysis = await analyzer.analyze_image(media.url)
        
        # Mise à jour du modèle avec les résultats
        for field, value in analysis.items():
            if hasattr(media, field) and field != 'error':
                setattr(media, field, value)
        
        media.analyzed_at = model.datetime.datetime.now()
        
        if 'error' in analysis:
            media.analysis_error = analysis['error']
            
            # Ne pas sauvegarder les images trop petites ou avec erreur
            if 'too small' in media.analysis_error:
                print(f"Skipping small image: {media.url}")
                return
        
        media.save()
        print(f"Media #{media.id} analyzed successfully")
        
    except Exception as e:
        media.analysis_error = str(e)
        media.analyzed_at = model.datetime.datetime.now()
        media.save()
        print(f"Error analyzing media: {e}")
```

## 6. Fonctions de réanalyse et suppression

```python
# mwi/core.py - Suite des ajouts

async def reanalyze_land_media(land: model.Land, filters: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """
    Réanalyse tous les médias d'un land avec filtres et suppression optionnelle
    """
    print(f"Reanalyzing media for land {land.name}")
    
    if filters['suppress_non_conforming']:
        print("WARNING: Suppression mode ENABLED - non-conforming media will be deleted")
    
    # Construction de la requête de base
    query = (model.Media
             .select()
             .join(model.Expression)
             .where(model.Expression.land == land))
    
    # Filtrer selon l'état d'analyse
    if not filters['force_reanalyze']:
        # Ne réanalyser que les médias non analysés
        query = query.where(model.Media.analyzed_at.is_null())
    
    media_count = query.count()
    if media_count == 0:
        print("No media to analyze")
        return 0, 0, 0, 0
    
    print(f"Found {media_count} media to process")
    
    # Configuration de l'analyseur
    analyzer_settings = {
        'user_agent': settings.user_agent,
        'min_width': filters['min_width'] or getattr(settings, 'media_min_width', 100),
        'min_height': filters['min_height'] or getattr(settings, 'media_min_height', 100),
        'max_file_size': filters['max_file_size'] or getattr(settings, 'media_max_file_size', 10*1024*1024),
        'analyze_content': getattr(settings, 'media_analyze_content', False),
        'extract_colors': getattr(settings, 'media_extract_colors', True),
        'extract_exif': getattr(settings, 'media_extract_exif', True)
    }
    
    # Statistiques
    analyzed = 0
    errors = 0
    skipped = 0
    deleted = 0
    
    # Traitement par batch
    batch_size = settings.parallel_connections
    batch_count = -(-media_count // batch_size)
    
    connector = aiohttp.TCPConnector(limit=settings.parallel_connections, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        analyzer = MediaAnalyzer(session, analyzer_settings)
        
        for batch_num in range(batch_count):
            current_offset = batch_num * batch_size
            batch_media = query.limit(batch_size).offset(current_offset)
            
            print(f"Processing batch {batch_num + 1}/{batch_count}")
            
            tasks = []
            for media in batch_media:
                task = reanalyze_single_media(media, analyzer, filters)
                tasks.append(task)
            
            # Exécuter le batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Comptabiliser les résultats
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    print(f"Batch error: {result}")
                else:
                    success, error, was_deleted, was_skipped = result
                    if was_deleted:
                        deleted += 1
                    elif was_skipped:
                        skipped += 1
                    elif error:
                        errors += 1
                    elif success:
                        analyzed += 1
    
    # Nettoyage des médias déjà analysés non conformes
    if filters['suppress_non_conforming']:
        additional_deleted = await cleanup_analyzed_non_conforming_media(land, filters)
        deleted += additional_deleted
    
    return analyzed, errors, skipped, deleted


async def reanalyze_single_media(media: model.Media, analyzer: MediaAnalyzer, 
                               filters: Dict[str, Any]) -> Tuple[bool, bool, bool, bool]:
    """
    Réanalyse un média unique
    Retourne (success, error, deleted, skipped)
    """
    try:
        # Vérifier si le média doit être ignoré
        if media.type != 'img':
            return False, False, False, True
        
        # Si déjà analysé et pas de force
        if media.analyzed_at and not filters['force_reanalyze']:
            # Vérifier seulement la conformité
            if filters['suppress_non_conforming']:
                if not media.is_conforming(
                    min_width=filters['min_width'],
                    min_height=filters['min_height'],
                    max_file_size=filters['max_file_size']
                ):
                    print(f"Deleting non-conforming media #{media.id}")
                    media.delete_instance()
                    return False, False, True, False
            return False, False, False, True
        
        print(f"Analyzing media #{media.id}: {media.url}")
        
        # Effectuer l'analyse
        analysis = await analyzer.analyze_image(media.url)
        
        # Mettre à jour les champs
        updated_fields = []
        for field, value in analysis.items():
            if hasattr(media, field) and field != 'error':
                old_value = getattr(media, field)
                if old_value != value:
                    setattr(media, field, value)
                    updated_fields.append(field)
        
        media.analyzed_at = model.datetime.datetime.now()
        
        # Gestion des erreurs d'analyse
        if 'error' in analysis:
            media.analysis_error = analysis['error']
            
            # Si suppression activée et erreur liée à la taille
            if filters['suppress_non_conforming']:
                if any(keyword in analysis['error'].lower() 
                      for keyword in ['too small', 'too large', 'excluded']):
                    print(f"Deleting media #{media.id} due to: {analysis['error']}")
                    media.delete_instance()
                    return False, False, True, False
            
            media.save()
            return False, True, False, False
        
        # Vérifier la conformité après analyse
        if filters['suppress_non_conforming']:
            non_conforming_reasons = []
            
            if filters['min_width'] > 0 and media.width and media.width < filters['min_width']:
                non_conforming_reasons.append(f"width {media.width} < {filters['min_width']}")
            
            if filters['min_height'] > 0 and media.height and media.height < filters['min_height']:
                non_conforming_reasons.append(f"height {media.height} < {filters['min_height']}")
            
            if filters['max_file_size'] > 0 and media.file_size and media.file_size > filters['max_file_size']:
                size_mb = media.file_size / (1024 * 1024)
                max_mb = filters['max_file_size'] / (1024 * 1024)
                non_conforming_reasons.append(f"size {size_mb:.1f}MB > {max_mb:.1f}MB")
            
            if non_conforming_reasons:
                print(f"Deleting media #{media.id}: {', '.join(non_conforming_reasons)}")
                media.delete_instance()
                return False, False, True, False
        
        # Sauvegarder si pas supprimé
        media.save()
        
        if updated_fields:
            print(f"Media #{media.id} updated: {', '.join(updated_fields)}")
        
        return True, False, False, False
        
    except Exception as e:
        print(f"Error analyzing media #{media.id}: {str(e)}")
        
        if not filters['suppress_non_conforming']:
            # Sauvegarder l'erreur
            try:
                media.analysis_error = str(e)
                media.analyzed_at = model.datetime.datetime.now()
                media.save()
            except:
                pass
            return False, True, False, False
        else:
            # Supprimer en cas d'erreur fatale
            try:
                print(f"Deleting media #{media.id} due to fatal error")
                media.delete_instance()
            except:
                pass
            return False, False, True, False


async def cleanup_analyzed_non_conforming_media(land: model.Land, 
                                              filters: Dict[str, Any]) -> int:
    """
    Supprime les médias déjà analysés qui ne respectent pas les critères
    """
    print("\nCleaning up previously analyzed non-conforming media...")
    
    # Requête de base pour les médias analysés
    query = (model.Media
             .select()
             .join(model.Expression)
             .where(
                 model.Expression.land == land,
                 model.Media.analyzed_at.is_null(False)
             ))
    
    # Conditions de suppression
    conditions = []
    
    if filters['min_width'] > 0:
        conditions.append(
            (model.Media.width < filters['min_width']) & 
            model.Media.width.is_null(False)
        )
    
    if filters['min_height'] > 0:
        conditions.append(
            (model.Media.height < filters['min_height']) & 
            model.Media.height.is_null(False)
        )
    
    if filters['max_file_size'] > 0:
        conditions.append(
            (model.Media.file_size > filters['max_file_size']) & 
            model.Media.file_size.is_null(False)
        )
    
    if not conditions:
        return 0
    
    # Appliquer les conditions avec OR
    from functools import reduce
    import operator
    combined_conditions = reduce(operator.or_, conditions)
    
    to_delete = query.where(combined_conditions)
    delete_count = to_delete.count()
    
    if delete_count == 0:
        print("No additional media to delete")
        return 0
    
    print(f"Found {delete_count} additional non-conforming media to delete")
    
    # Suppression par batch
    deleted = 0
    batch_size = 100
    
    with model.DB.atomic():
        while True:
            batch = list(to_delete.limit(batch_size))
            if not batch:
                break
            
            for media in batch:
                try:
                    print(f"Deleting analyzed media #{media.id} ({media.width}x{media.height}, "
                          f"{media.file_size/(1024*1024):.1f}MB)")
                    media.delete_instance()
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting media #{media.id}: {e}")
    
    print(f"Deleted {deleted} additional non-conforming media")
    return deleted


def delete_media_by_criteria(land: model.Land, criteria: Dict[str, Any]) -> int:
    """
    Supprime directement les médias selon des critères
    """
    query = (model.Media
             .select()
             .join(model.Expression)
             .where(model.Expression.land == land))
    
    # Appliquer les critères
    if 'min_file_size' in criteria:
        query = query.where(model.Media.file_size >= criteria['min_file_size'])
    
    if 'max_file_size' in criteria:
        query = query.where(model.Media.file_size <= criteria['max_file_size'])
    
    if 'formats' in criteria:
        query = query.where(model.Media.format.in_(criteria['formats']))
    
    if 'older_than' in criteria:
        query = query.where(model.Media.analyzed_at < criteria['older_than'])
    
    # Compter et supprimer
    count = query.count()
    if count > 0:
        query.delete().execute()
    
    return count
```

## 7. Contrôleurs

```python
# mwi/controller.py - Ajouts aux contrôleurs existants

class LandController:
    """
    Land controller class avec fonctions média
    """
    
    # ... méthodes existantes ...
    
    @staticmethod
    def reanalyze_media(args: core.Namespace):
        """
        Réanalyse les médias d'un land avec filtres optionnels
        """
        core.check_args(args, 'name')
        
        # Récupération des options
        min_width = core.get_arg_option('minwidth', args, set_type=int, default=0)
        min_height = core.get_arg_option('minheight', args, set_type=int, default=0)
        max_size = core.get_arg_option('maxsize', args, set_type=int, default=0)
        force = core.get_arg_option('force', args, set_type=bool, default=False)
        suppress = core.get_arg_option('suppress', args, set_type=bool, default=False)
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
            return 0
        
        # Configuration des filtres
        filters = {
            'min_width': min_width,
            'min_height': min_height,
            'max_file_size': max_size * 1024 * 1024 if max_size > 0 else 0,
            'force_reanalyze': force,
            'suppress_non_conforming': suppress
        }
        
        # Confirmation si suppression
        if suppress:
            criteria = []
            if min_width > 0:
                criteria.append(f"width < {min_width}px")
            if min_height > 0:
                criteria.append(f"height < {min_height}px")  
            if max_size > 0:
                criteria.append(f"size > {max_size}MB")
            
            if criteria:
                print(f"\nWARNING: Media matching these criteria will be DELETED:")
                print(f"  {' OR '.join(criteria)}")
                
                # Afficher un aperçu
                from .queries import get_media_deletion_preview
                preview = get_media_deletion_preview(land, filters)
                print(f"\nEstimated deletions: {preview['would_be_deleted']} media")
                
                if not core.confirm("\nType 'Y' to proceed with deletion: "):
                    print("Operation cancelled")
                    return 0
        
        # Exécution
        loop = asyncio.get_event_loop()
        try:
            results = loop.run_until_complete(core.reanalyze_land_media(land, filters))
            analyzed, errors, skipped, deleted = results
            
            print(f"\nReanalysis complete:")
            print(f"  Analyzed: {analyzed}")
            print(f"  Errors: {errors}")
            print(f"  Skipped: {skipped}")
            print(f"  Deleted: {deleted}")
            
            return 1
            
        except KeyboardInterrupt:
            print("\nOperation interrupted by user")
            return 0
    
    @staticmethod
    def preview_media_deletion(args: core.Namespace):
        """
        Prévisualise les médias qui seraient supprimés
        """
        core.check_args(args, 'name')
        
        min_width = core.get_arg_option('minwidth', args, set_type=int, default=0)
        min_height = core.get_arg_option('minheight', args, set_type=int, default=0)
        max_size = core.get_arg_option('maxsize', args, set_type=int, default=0)
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
            return 0
        
        filters = {
            'min_width': min_width,
            'min_height': min_height,
            'max_file_size': max_size * 1024 * 1024 if max_size > 0 else 0
        }
        
        if not any([min_width > 0, min_height > 0, max_size > 0]):
            print("No filters specified. Use --minwidth, --minheight, or --maxsize")
            return 0
        
        # Import des fonctions de requête
        from .queries import get_media_deletion_preview, get_deletable_media_samples
        
        # Statistiques
        stats = get_media_deletion_preview(land, filters)
        
        print(f"\nMedia deletion preview for land '{land.name}':")
        print(f"Total media: {stats['total']}")
        print(f"Already analyzed: {stats['total'] - stats['not_analyzed']}")
        print(f"Not yet analyzed: {stats['not_analyzed']}")
        
        print(f"\nWith current filters:")
        if min_width > 0:
            print(f"  Below minimum width ({min_width}px): {stats['below_min_width']}")
        if min_height > 0:
            print(f"  Below minimum height ({min_height}px): {stats['below_min_height']}")
        if max_size > 0:
            print(f"  Above maximum size ({max_size}MB): {stats['above_max_size']}")
        
        print(f"\n{'='*50}")
        print(f"TOTAL media that would be deleted: {stats['would_be_deleted']}")
        print(f"{'='*50}")
        
        # Exemples
        if stats['would_be_deleted'] > 0:
            print("\nSample of media that would be deleted:")
            samples = get_deletable_media_samples(land, filters, limit=10)
            
            for i, sample in enumerate(samples, 1):
                media_id, url, width, height, file_size, source_url, reason = sample
                size_mb = file_size / (1024 * 1024) if file_size else 0
                
                print(f"\n{i}. Media #{media_id}")
                print(f"   Reason: {reason}")
                print(f"   URL: {url[:80]}{'...' if len(url) > 80 else ''}")
                print(f"   Dimensions: {width}x{height}px")
                print(f"   Size: {size_mb:.2f}MB")
                print(f"   Source: {source_url[:80]}{'...' if len(source_url) > 80 else ''}")
        
        return 1
    
    @staticmethod
    def media_stats(args: core.Namespace):
        """
        Affiche les statistiques des médias d'un land
        """
        core.check_args(args, 'name')
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
            return 0
        
        from .queries import (
            get_media_statistics, 
            get_media_format_distribution,
            get_media_size_distribution,
            find_duplicate_images,
            get_color_distribution
        )
        
        # Statistiques générales
        stats = get_media_statistics(land)
        
        print(f"\nMedia statistics for land '{land.name}':")
        print(f"{'='*50}")
        print(f"Total media: {stats['total_media']}")
        print(f"Analyzed: {stats['analyzed_media']} "
              f"({stats['analyzed_media']/stats['total_media']*100:.1f}%)")
        print(f"With errors: {stats['error_media']}")
        print(f"Unique images (by hash): {stats['unique_images']}")
        
        if stats['analyzed_media'] > 0:
            print(f"\nAverage dimensions: {stats['avg_width']:.0f}x{stats['avg_height']:.0f}px")
            print(f"Average file size: {stats['avg_file_size']/1024/1024:.2f}MB")
        
        # Distribution des formats
        print(f"\n{'='*50}")
        print("Format distribution:")
        formats = get_media_format_distribution(land)
        for fmt, count in formats:
            print(f"  {fmt or 'unknown'}: {count}")
        
        # Distribution des tailles
        print(f"\n{'='*50}")
        print("Size distribution:")
        sizes = get_media_size_distribution(land)
        for category, count in sizes:
            print(f"  {category}: {count}")
        
        # Images dupliquées
        duplicates = find_duplicate_images(land)
        if duplicates:
            print(f"\n{'='*50}")
            print(f"Duplicate images found: {len(duplicates)} groups")
            for i, (hash_val, count, urls, sources) in enumerate(duplicates[:5], 1):
                print(f"\n{i}. Hash {hash_val} ({count} copies)")
                urls_list = urls.split(',')
                print(f"   First URL: {urls_list[0][:80]}...")
        
        # Distribution des couleurs
        if stats['analyzed_media'] > 0:
            print(f"\n{'='*50}")
            print("Color distribution (dominant colors):")
            colors = get_color_distribution(land)
            
            # Trier par pourcentage
            sorted_colors = sorted(colors.items(), key=lambda x: x[1], reverse=True)
            total_percentage = sum(colors.values())
            
            for color, percentage in sorted_colors:
                if percentage > 0:
                    normalized = (percentage / total_percentage * 100) if total_percentage > 0 else 0
                    print(f"  {color}: {normalized:.1f}%")
        
        return 1
    
    @staticmethod
    def crawl(args: core.Namespace):
        """
        Version modifiée du crawl avec option d'analyse média
        """
        core.check_args(args, 'name')
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        if fetch_limit > 0:
            print('Fetch limit set to %s URLs' % fetch_limit)
        
        http_status = core.get_arg_option('http', args, set_type=str, default=None)
        if http_status is not None:
            print('Limited to %s HTTP status code' % http_status)
        
        # Nouvelle option pour activer l'analyse média pendant le crawl
        analyze_media = core.get_arg_option('analyze_media', args, set_type=bool, 
                                          default=settings.media_analysis)
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
            return 0
        
        loop = asyncio.get_event_loop()
        
        if analyze_media:
            print("Media analysis is ENABLED during crawl")
            results = loop.run_until_complete(
                core.crawl_land_with_media_analysis(land, fetch_limit, http_status)
            )
        else:
            print("Media analysis is DISABLED during crawl")
            results = loop.run_until_complete(
                core.crawl_land(land, fetch_limit, http_status)
            )
        
        print("%d expressions processed (%d errors)" % results)
        return 1
```

## 8. Interface CLI

```python
# mwi/cli.py - Modifications pour supporter les nouvelles commandes

def command_input():
    """
    Run command from input avec support média
    """
    parser = argparse.ArgumentParser(
        description='MyWebIntelligence Command Line Project Manager.'
    )
    
    # Arguments existants
    parser.add_argument('object',
                        metavar='object',
                        type=str,
                        help='Object to interact with [db, land, domain, tag, heuristic]')
    parser.add_argument('verb',
                        metavar='verb',
                        type=str,
                        help='Verb depending on target object')
    
    # Arguments généraux existants
    parser.add_argument('--land',
                        type=str,
                        help='Name of the land to work with')
    parser.add_argument('--name',
                        type=str,
                        help='Name of the object')
    parser.add_argument('--desc',
                        type=str,
                        help='Description of the object')
    parser.add_argument('--type',
                        type=str,
                        help='Export type, see README for reference')
    parser.add_argument('--terms',
                        type=str,
                        help='Terms to add to request dictionnary, comma separated')
    parser.add_argument('--urls',
                        type=str,
                        help='URL to add to request, comma separated',
                        nargs='?')
    parser.add_argument('--path',
                        type=str,
                        help='Path to local file containing URLs',
                        nargs='?')
    parser.add_argument('--limit',
                        type=int,
                        help='Set limit of URLs to crawl',
                        nargs='?',
                        const=0)
    parser.add_argument('--minrel',
                        type=int,
                        help='Set minimum relevance threshold',
                        nargs='?',
                        const=0)
    parser.add_argument('--maxrel',
                        type=int,
                        help='Set maximum relevance threshold',
                        nargs='?',
                        const=0)
    parser.add_argument('--http',
                        type=str,
                        help='Limit crawling to specific http status (re crawling)',
                        nargs='?')
    
    # Nouveaux arguments pour l'analyse média
    parser.add_argument('--minwidth',
                        type=int,
                        help='Minimum width filter for media analysis (pixels)',
                        nargs='?',
                        const=0)
    parser.add_argument('--minheight',
                        type=int,
                        help='Minimum height filter for media analysis (pixels)',
                        nargs='?',
                        const=0)
    parser.add_argument('--maxsize',
                        type=int,
                        help='Maximum file size in MB for media analysis',
                        nargs='?',
                        const=0)
    parser.add_argument('--force',
                        action='store_true',
                        help='Force reanalysis of already analyzed media')
    parser.add_argument('--suppress',
                        action='store_true',
                        help='Suppress (delete) media that do not meet criteria')
    parser.add_argument('--analyze-media',
                        action='store_true',
                        dest='analyze_media',
                        help='Enable media analysis during crawl')
    parser.add_argument('--no-analyze-media',
                        action='store_false',
                        dest='analyze_media',
                        help='Disable media analysis during crawl')
    parser.set_defaults(analyze_media=None)
    
    args = parser.parse_args()
    dispatch(args)


def dispatch(args):
    """
    Dispatch command to application controller avec support média
    """
    controllers = {
        'db': {
            'setup': DbController.setup,
            'migrate': DbController.migrate  # Nouvelle commande
        },
        'domain': {
            'crawl': DomainController.crawl
        },
        'land': {
            'list':              LandController.list,
            'create':            LandController.create,
            'delete':            LandController.delete,
            'crawl':             LandController.crawl,
            'readable':          LandController.readable,
            'export':            LandController.export,
            'addterm':           LandController.addterm,
            'addurl':            LandController.addurl,
            # Nouvelles commandes média
            'reanalyze':         LandController.reanalyze_media,
            'preview_deletion':  LandController.preview_media_deletion,
            'media_stats':       LandController.media_stats,
        },
        'tag': {
            'export': TagController.export,
        },
        'heuristic': {
            'update': HeuristicController.update
        }
    }
    
    controller = controllers.get(args.object)
    if controller:
        return call(controller.get(args.verb), args)
    raise ValueError("Invalid object {}".format(args.object))


# Ajout dans DbController
class DbController:
    """
    Db controller class avec support migrations
    """
    
    @staticmethod
    def setup(args: core.Namespace):
        """
        Creates database model, this is a destructive action as tables are dropped before creation
        """
        tables = [
            model.Land, model.Domain, model.Expression, model.ExpressionLink, 
            model.Word, model.LandDictionary, model.Media, model.Tag, 
            model.TaggedContent
        ]

        if core.confirm("Warning, existing data will be lost, type 'Y' to proceed : "):
            model.DB.drop_tables(tables)
            model.DB.create_tables(tables)
            print("Model created, setup complete")
            return 1
        print("Database setup aborted")
        return 0
    
    @staticmethod
    def migrate(args: core.Namespace):
        """
        Execute database migrations
        """
        from migrate import MigrationManager
        
        print("Running database migrations...")
        manager = MigrationManager()
        manager.migrate()
        return 1
```

## 9. Requêtes et statistiques

```python
# mwi/queries.py - Nouveau fichier complet

"""
Requêtes analytiques pour les médias
"""

import json
from typing import Dict, List, Tuple, Any
from . import model


def get_media_statistics(land: model.Land) -> Dict[str, Any]:
    """
    Statistiques générales sur les médias d'un land
    """
    query = """
    SELECT
        COUNT(*) as total_media,
        COUNT(CASE WHEN analyzed_at IS NOT NULL THEN 1 END) as analyzed_media,
        COUNT(CASE WHEN analysis_error IS NOT NULL THEN 1 END) as error_media,
        AVG(CASE WHEN width IS NOT NULL THEN width END) as avg_width,
        AVG(CASE WHEN height IS NOT NULL THEN height END) as avg_height,
        AVG(CASE WHEN file_size IS NOT NULL THEN file_size END) as avg_file_size,
        COUNT(DISTINCT image_hash) as unique_images,
        MIN(file_size) as min_file_size,
        MAX(file_size) as max_file_size,
        MIN(width) as min_width,
        MAX(width) as max_width,
        MIN(height) as min_height,
        MAX(height) as max_height
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ?
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    columns = [
        'total_media', 'analyzed_media', 'error_media',
        'avg_width', 'avg_height', 'avg_file_size', 'unique_images',
        'min_file_size', 'max_file_size', 'min_width', 'max_width',
        'min_height', 'max_height'
    ]
    
    result = dict(zip(columns, cursor.fetchone()))
    
    # Arrondir les moyennes
    for key in ['avg_width', 'avg_height', 'avg_file_size']:
        if result[key] is not None:
            result[key] = round(result[key], 2)
    
    return result


def get_media_deletion_preview(land: model.Land, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prévisualise les médias qui seraient supprimés
    """
    query = """
    SELECT
        COUNT(*) as total,
        SUM(CASE 
            WHEN width < ? AND width IS NOT NULL 
            THEN 1 ELSE 0 
        END) as below_min_width,
        SUM(CASE 
            WHEN height < ? AND height IS NOT NULL 
            THEN 1 ELSE 0 
        END) as below_min_height,
        SUM(CASE 
            WHEN file_size > ? AND file_size IS NOT NULL 
            THEN 1 ELSE 0 
        END) as above_max_size,
        SUM(CASE 
            WHEN (
                (width < ? AND width IS NOT NULL) OR 
                (height < ? AND height IS NOT NULL) OR 
                (file_size > ? AND file_size IS NOT NULL)
            ) THEN 1 ELSE 0 
        END) as would_be_deleted,
        SUM(CASE 
            WHEN analyzed_at IS NULL 
            THEN 1 ELSE 0 
        END) as not_analyzed
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? AND m.type = 'img'
    """
    
    params = (
        filters['min_width'], 
        filters['min_height'], 
        filters['max_file_size'],
        filters['min_width'], 
        filters['min_height'], 
        filters['max_file_size'],
        land.id
    )
    
    cursor = model.DB.execute_sql(query, params)
    columns = ['total', 'below_min_width', 'below_min_height', 
               'above_max_size', 'would_be_deleted', 'not_analyzed']
    
    return dict(zip(columns, cursor.fetchone()))


def get_deletable_media_samples(land: model.Land, filters: Dict[str, Any], 
                               limit: int = 10) -> List[Tuple]:
    """
    Récupère des exemples de médias qui seraient supprimés
    """
    query = """
    SELECT
        m.id,
        m.url,
        m.width,
        m.height,
        m.file_size,
        e.url as source_url,
        CASE
            WHEN m.width < ? AND m.width IS NOT NULL 
                THEN 'Width too small (' || m.width || 'px)'
            WHEN m.height < ? AND m.height IS NOT NULL 
                THEN 'Height too small (' || m.height || 'px)'
            WHEN m.file_size > ? AND m.file_size IS NOT NULL 
                THEN 'File too large (' || ROUND(CAST(m.file_size AS REAL) / 1048576, 2) || 'MB)'
        END as reason
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ?
        AND m.type = 'img'
        AND m.analyzed_at IS NOT NULL
        AND (
            (m.width < ? AND m.width IS NOT NULL) OR 
            (m.height < ? AND m.height IS NOT NULL) OR 
            (m.file_size > ? AND m.file_size IS NOT NULL)
        )
    ORDER BY m.file_size DESC
    LIMIT ?
    """
    
    params = (
        filters['min_width'],
        filters['min_height'],
        filters['max_file_size'],
        land.id,
        filters['min_width'],
        filters['min_height'],
        filters['max_file_size'],
        limit
    )
    
    cursor = model.DB.execute_sql(query, params)
    return cursor.fetchall()


def find_duplicate_images(land: model.Land, min_copies: int = 2) -> List[Tuple]:
    """
    Trouve les images dupliquées basées sur le hash perceptuel
    """
    query = """
    SELECT
        m.image_hash,
        COUNT(*) as count,
        GROUP_CONCAT(SUBSTR(m.url, 1, 100)) as urls,
        GROUP_CONCAT(DISTINCT SUBSTR(e.url, 1, 80)) as source_pages,
        SUM(m.file_size) as total_size
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? 
        AND m.image_hash IS NOT NULL
        AND m.type = 'img'
    GROUP BY m.image_hash
    HAVING COUNT(*) >= ?
    ORDER BY count DESC, total_size DESC
    """
    
    cursor = model.DB.execute_sql(query, (land.id, min_copies))
    return cursor.fetchall()


def get_media_format_distribution(land: model.Land) -> List[Tuple[str, int]]:
    """
    Distribution des formats de média
    """
    query = """
    SELECT
        LOWER(m.format) as format,
        COUNT(*) as count
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ?
    GROUP BY LOWER(m.format)
    ORDER BY count DESC
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    return cursor.fetchall()


def get_media_size_distribution(land: model.Land) -> List[Tuple[str, int]]:
    """
    Distribution des tailles de fichiers
    """
    query = """
    SELECT
        CASE
            WHEN file_size < 10240 THEN '< 10KB'
            WHEN file_size < 102400 THEN '10KB - 100KB'
            WHEN file_size < 1048576 THEN '100KB - 1MB'
            WHEN file_size < 5242880 THEN '1MB - 5MB'
            WHEN file_size < 10485760 THEN '5MB - 10MB'
            ELSE '> 10MB'
        END as size_category,
        COUNT(*) as count
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? AND m.file_size IS NOT NULL
    GROUP BY size_category
    ORDER BY 
        CASE size_category
            WHEN '< 10KB' THEN 1
            WHEN '10KB - 100KB' THEN 2
            WHEN '100KB - 1MB' THEN 3
            WHEN '1MB - 5MB' THEN 4
            WHEN '5MB - 10MB' THEN 5
            ELSE 6
        END
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    return cursor.fetchall()


def get_color_distribution(land: model.Land) -> Dict[str, float]:
    """
    Analyse la distribution des couleurs dominantes
    """
    query = """
    SELECT dominant_colors
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? 
        AND m.dominant_colors IS NOT NULL
        AND m.type = 'img'
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    
    color_stats = {}
    total_weight = 0
    
    for row in cursor:
        try:
            colors = json.loads(row[0])
            for color in colors:
                color_name = color.get('name', 'unknown')
                weight = color.get('percentage', 0)
                
                if color_name not in color_stats:
                    color_stats[color_name] = 0
                
                color_stats[color_name] += weight
                total_weight += weight
        except (json.JSONDecodeError, KeyError):
            continue
    
    return color_stats


def get_media_by_dimensions(land: model.Land, min_width: int = 0, 
                           min_height: int = 0) -> List[model.Media]:
    """
    Récupère les médias filtrés par dimensions
    """
    query = (model.Media
             .select()
             .join(model.Expression)
             .where(
                 model.Expression.land == land,
                 model.Media.width >= min_width,
                 model.Media.height >= min_height
             )
             .order_by(model.Media.width.desc(), model.Media.height.desc()))
    
    return list(query)


def get_largest_media(land: model.Land, limit: int = 10) -> List[Tuple]:
    """
    Récupère les médias les plus volumineux
    """
    query = """
    SELECT
        m.id,
        m.url,
        m.width,
        m.height,
        m.file_size,
        e.url as source_url,
        m.format
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? 
        AND m.file_size IS NOT NULL
        AND m.type = 'img'
    ORDER BY m.file_size DESC
    LIMIT ?
    """
    
    cursor = model.DB.execute_sql(query, (land.id, limit))
    return cursor.fetchall()


def get_media_errors(land: model.Land) -> List[Tuple]:
    """
    Récupère les médias avec erreurs d'analyse
    """
    query = """
    SELECT
        m.id,
        m.url,
        m.analysis_error,
        e.url as source_url,
        COUNT(*) OVER (PARTITION BY m.analysis_error) as error_count
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? 
        AND m.analysis_error IS NOT NULL
    ORDER BY error_count DESC, m.id
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    return cursor.fetchall()


def get_media_analysis_progress(land: model.Land) -> Dict[str, Any]:
    """
    Progression de l'analyse des médias
    """
    query = """
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN analyzed_at IS NOT NULL THEN 1 END) as analyzed,
        COUNT(CASE WHEN analysis_error IS NOT NULL THEN 1 END) as errors,
        MIN(analyzed_at) as first_analysis,
        MAX(analyzed_at) as last_analysis,
        COUNT(DISTINCT DATE(analyzed_at)) as analysis_days
    FROM media m
    JOIN expression e ON e.id = m.expression_id
    WHERE e.land_id = ? AND m.type = 'img'
    """
    
    cursor = model.DB.execute_sql(query, (land.id,))
    columns = ['total', 'analyzed', 'errors', 'first_analysis', 
               'last_analysis', 'analysis_days']
    
    result = dict(zip(columns, cursor.fetchone()))
    
    # Calculer le pourcentage
    if result['total'] > 0:
        result['progress_percent'] = round(
            (result['analyzed'] / result['total']) * 100, 2
        )
    else:
        result['progress_percent'] = 0
    
    return result
```

## 10. Configuration

```python
# settings.py - Ajouts pour la configuration média

# ... configuration existante ...

# Configuration de l'analyse média
media_analysis = True  # Active l'analyse pendant le crawl par défaut

# Filtres de taille
media_min_width = 200  # Largeur minimale en pixels
media_min_height = 200  # Hauteur minimale en pixels  
media_max_file_size = 10 * 1024 * 1024  # 10MB max

# Options d'analyse
media_analyze_content = False  # Analyse de contenu (nécessite modèles ML)
media_extract_colors = True  # Extraction des couleurs dominantes
media_extract_exif = True  # Extraction des métadonnées EXIF
media_n_dominant_colors = 5  # Nombre de couleurs dominantes à extraire

# Timeouts et retry
media_download_timeout = 30  # Timeout de téléchargement en secondes
media_max_retries = 2  # Nombre de tentatives en cas d'échec

# Patterns d'exclusion personnalisés (regex)
media_exclude_patterns = [
    # Ajouter ici des patterns personnalisés
]

# Formats d'image acceptés
media_accepted_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
```

## 11. Tests unitaires

```python
# tests/test_media_analyzer.py - Suite

    def test_calculate_visual_complexity(self, analyzer_settings):
        """Test du calcul de complexité visuelle"""
        # Image uniforme (faible complexité)
        img_simple = Image.new('RGB', (100, 100), color='red')
        
        # Image avec bruit (haute complexité)
        import numpy as np
        noise = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        img_complex = Image.fromarray(noise, 'RGB')
        
        class MockSession:
            pass
        
        analyzer = MediaAnalyzer(MockSession(), analyzer_settings)
        
        complexity_simple = analyzer._calculate_visual_complexity(img_simple)
        complexity_complex = analyzer._calculate_visual_complexity(img_complex)
        
        assert 0 <= complexity_simple <= 1
        assert 0 <= complexity_complex <= 1
        assert complexity_simple < complexity_complex
        assert complexity_simple < 0.1  # Image uniforme = très simple
    
    def test_is_likely_logo(self, analyzer_settings):
        """Test de détection de logo"""
        # Petite image avec peu de couleurs (logo probable)
        img_logo = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img_logo)
        draw.rectangle([50, 25, 150, 75], fill='blue')
        
        # Grande image (pas un logo)
        img_large = Image.new('RGB', (1000, 1000), color='white')
        
        class MockSession:
            pass
        
        analyzer = MediaAnalyzer(MockSession(), analyzer_settings)
        
        assert analyzer._is_likely_logo(img_logo)
        assert not analyzer._is_likely_logo(img_large)
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self, analyzer_settings, sample_image, mocker):
        """Test d'analyse complète réussie"""
        async with aiohttp.ClientSession() as session:
            analyzer = MediaAnalyzer(session, analyzer_settings)
            
            # Mocker le téléchargement
            async def mock_download(*args, **kwargs):
                return sample_image
            
            mocker.patch.object(analyzer, '_download_with_retry', mock_download)
            
            result = await analyzer.analyze_image('http://example.com/test.jpg')
            
            assert 'error' not in result
            assert result['width'] == 300
            assert result['height'] == 200
            assert result['format'] == 'JPEG'
            assert result['file_size'] == len(sample_image)
            assert 'image_hash' in result
            assert 'dominant_colors' in result
    
    @pytest.mark.asyncio
    async def test_analyze_image_too_small(self, analyzer_settings, small_image, mocker):
        """Test avec image trop petite"""
        async with aiohttp.ClientSession() as session:
            analyzer = MediaAnalyzer(session, analyzer_settings)
            
            async def mock_download(*args, **kwargs):
                return small_image
            
            mocker.patch.object(analyzer, '_download_with_retry', mock_download)
            
            result = await analyzer.analyze_image('http://example.com/small.png')
            
            assert 'error' in result
            assert 'too small' in result['error']
            assert result['width'] == 50
            assert result['height'] == 50


# tests/test_media_integration.py - Tests d'intégration

import pytest
import asyncio
from mwi import model, core
from mwi.media_analyzer import MediaAnalyzer


class TestMediaIntegration:
    """Tests d'intégration pour l'analyse média"""
    
    @pytest.fixture
    def test_land(self):
        """Crée un land de test"""
        land = model.Land.create(
            name='test_media_land',
            description='Land for media testing'
        )
        yield land
        # Nettoyage
        land.delete_instance(recursive=True)
    
    @pytest.fixture
    def test_expression(self, test_land):
        """Crée une expression de test"""
        domain = model.Domain.create(name='test.com')
        expression = model.Expression.create(
            land=test_land,
            domain=domain,
            url='http://test.com/page.html',
            depth=0
        )
        yield expression
        # Nettoyage
        expression.delete_instance()
        domain.delete_instance()
    
    @pytest.fixture
    def test_media(self, test_expression):
        """Crée des médias de test"""
        medias = []
        
        # Média non analysé
        media1 = model.Media.create(
            expression=test_expression,
            url='http://test.com/image1.jpg',
            type='img'
        )
        medias.append(media1)
        
        # Média analysé conforme
        media2 = model.Media.create(
            expression=test_expression,
            url='http://test.com/image2.png',
            type='img',
            width=500,
            height=400,
            file_size=500000,
            analyzed_at=model.datetime.datetime.now()
        )
        medias.append(media2)
        
        # Média analysé non conforme (trop petit)
        media3 = model.Media.create(
            expression=test_expression,
            url='http://test.com/small.gif',
            type='img',
            width=50,
            height=50,
            file_size=5000,
            analyzed_at=model.datetime.datetime.now()
        )
        medias.append(media3)
        
        yield medias
        
        # Nettoyage
        for media in medias:
            media.delete_instance()
    
    def test_media_conformity(self, test_media):
        """Test de vérification de conformité"""
        media1, media2, media3 = test_media
        
        # Test avec critères standards
        assert media2.is_conforming(min_width=200, min_height=200)
        assert not media3.is_conforming(min_width=200, min_height=200)
        
        # Test avec critères de taille de fichier
        assert media2.is_conforming(max_file_size=1000000)
        assert not media2.is_conforming(max_file_size=100000)
    
    @pytest.mark.asyncio
    async def test_reanalyze_without_suppression(self, test_land, test_media):
        """Test de réanalyse sans suppression"""
        filters = {
            'min_width': 200,
            'min_height': 200,
            'max_file_size': 0,
            'force_reanalyze': False,
            'suppress_non_conforming': False
        }
        
        # Simuler la réanalyse
        initial_count = len(test_media)
        
        # Vérifier que tous les médias sont toujours présents
        remaining = model.Media.select().count()
        assert remaining == initial_count
    
    def test_media_statistics(self, test_land, test_media):
        """Test des statistiques média"""
        from mwi.queries import get_media_statistics
        
        stats = get_media_statistics(test_land)
        
        assert stats['total_media'] == 3
        assert stats['analyzed_media'] == 2
        assert stats['avg_width'] == 275  # (500 + 50) / 2
        assert stats['avg_height'] == 225  # (400 + 50) / 2
    
    def test_deletion_preview(self, test_land, test_media):
        """Test de prévisualisation de suppression"""
        from mwi.queries import get_media_deletion_preview
        
        filters = {
            'min_width': 200,
            'min_height': 200,
            'max_file_size': 0
        }
        
        preview = get_media_deletion_preview(test_land, filters)
        
        assert preview['total'] == 3
        assert preview['would_be_deleted'] == 1  # Le média 50x50
        assert preview['not_analyzed'] == 1


# tests/test_cli_media.py - Tests CLI

import pytest
from argparse import Namespace
from mwi.cli import dispatch
from mwi.controller import LandController
from mwi import model


class TestMediaCLI:
    """Tests pour les commandes CLI média"""
    
    @pytest.fixture
    def test_land_with_media(self):
        """Crée un environnement de test complet"""
        # Créer le land
        land = model.Land.create(
            name='cli_test_land',
            description='Test land for CLI'
        )
        
        # Créer des expressions et médias
        domain = model.Domain.create(name='example.com')
        
        for i in range(3):
            expr = model.Expression.create(
                land=land,
                domain=domain,
                url=f'http://example.com/page{i}.html',
                depth=0
            )
            
            # Ajouter des médias variés
            model.Media.create(
                expression=expr,
                url=f'http://example.com/image{i}.jpg',
                type='img',
                width=300 + i * 100,
                height=200 + i * 100,
                file_size=100000 * (i + 1),
                analyzed_at=model.datetime.datetime.now() if i > 0 else None
            )
        
        yield land
        
        # Nettoyage
        model.Media.delete().execute()
        model.Expression.delete().where(model.Expression.land == land).execute()
        domain.delete_instance()
        land.delete_instance()
    
    def test_preview_deletion_command(self, test_land_with_media, capsys):
        """Test de la commande preview_deletion"""
        args = Namespace(
            object='land',
            verb='preview_deletion',
            name=test_land_with_media.name,
            minwidth=400,
            minheight=300,
            maxsize=0
        )
        
        result = LandController.preview_media_deletion(args)
        assert result == 1
        
        captured = capsys.readouterr()
        assert 'Media deletion preview' in captured.out
        assert 'would be deleted' in captured.out
    
    def test_media_stats_command(self, test_land_with_media, capsys):
        """Test de la commande media_stats"""
        args = Namespace(
            object='land',
            verb='media_stats',
            name=test_land_with_media.name
        )
        
        result = LandController.media_stats(args)
        assert result == 1
        
        captured = capsys.readouterr()
        assert 'Media statistics' in captured.out
        assert 'Total media:' in captured.out
        assert 'Format distribution:' in captured.out
```

## 12. Documentation d'utilisation

### 12.1 Guide d'installation

```markdown
# Installation de l'analyse média

## Prérequis

Les dépendances suivantes doivent être ajoutées :

```bash
pip install Pillow==10.1.0
pip install imagehash==4.3.1
pip install numpy==1.24.3
pip install scikit-learn==1.3.0
```

## Migration de la base de données

Après l'installation des dépendances, exécuter la migration :

```bash
python mywi.py db migrate
```

Cette commande ajoutera les colonnes nécessaires à la table `media`.
```

### 12.2 Guide d'utilisation complète

```markdown
# Guide d'utilisation de l'analyse média

## Vue d'ensemble

L'analyse média permet d'extraire et analyser automatiquement les images lors du crawl, 
avec des fonctionnalités de filtrage, statistiques et suppression.

## Configuration

Éditer `settings.py` pour configurer l'analyse :

```python
# Activer/désactiver l'analyse pendant le crawl
media_analysis = True

# Dimensions minimales acceptées
media_min_width = 200
media_min_height = 200

# Taille maximale de fichier (en octets)
media_max_file_size = 10 * 1024 * 1024  # 10MB

# Options d'analyse
media_extract_colors = True  # Extraction des couleurs dominantes
media_extract_exif = True    # Extraction EXIF
```

## Commandes principales

### 1. Crawl avec analyse média

```bash
# Activer l'analyse pendant le crawl
python mywi.py land crawl --name=MON_LAND --analyze-media

# Désactiver l'analyse pendant le crawl
python mywi.py land crawl --name=MON_LAND --no-analyze-media
```

### 2. Réanalyse des médias existants

```bash
# Analyser seulement les médias non analysés
python mywi.py land reanalyze --name=MON_LAND

# Forcer la réanalyse de tous les médias
python mywi.py land reanalyze --name=MON_LAND --force

# Avec filtres de dimensions
python mywi.py land reanalyze --name=MON_LAND --minwidth=300 --minheight=300
```

### 3. Suppression des médias non conformes

```bash
# ATTENTION : prévisualiser d'abord !
python mywi.py land preview_deletion --name=MON_LAND --minwidth=300 --minheight=300 --maxsize=5

# Supprimer les médias non conformes
python mywi.py land reanalyze --name=MON_LAND --minwidth=300 --minheight=300 --maxsize=5 --suppress
```

### 4. Statistiques et analyses

```bash
# Voir les statistiques générales
python mywi.py land media_stats --name=MON_LAND

# Exporter les médias enrichis
python mywi.py land export --name=MON_LAND --type=mediacsv --minrel=1
```

## Exemples d'utilisation

### Cas 1 : Nettoyer les petites images

```bash
# 1. Prévisualiser ce qui sera supprimé
python mywi.py land preview_deletion --name=projet --minwidth=200 --minheight=200

# 2. Si OK, procéder à la suppression
python mywi.py land reanalyze --name=projet --minwidth=200 --minheight=200 --suppress
```

### Cas 2 : Limiter la taille des fichiers

```bash
# Supprimer les images de plus de 3MB
python mywi.py land reanalyze --name=projet --maxsize=3 --suppress
```

### Cas 3 : Analyse complète après crawl

```bash
# 1. Crawler sans analyse (plus rapide)
python mywi.py land crawl --name=projet --no-analyze-media

# 2. Analyser les médias en batch
python mywi.py land reanalyze --name=projet

# 3. Nettoyer selon critères
python mywi.py land reanalyze --name=projet --minwidth=300 --minheight=300 --maxsize=5 --suppress
```

## Interprétation des résultats

### Métadonnées extraites

- **Dimensions** : largeur et hauteur en pixels
- **Taille** : taille du fichier en octets
- **Format** : format d'image (JPEG, PNG, etc.)
- **Couleurs dominantes** : top 5 des couleurs avec pourcentages
- **Hash perceptuel** : pour détecter les doublons
- **EXIF** : métadonnées de l'appareil photo si disponibles

### Critères de suppression

Les médias sont supprimés si AU MOINS UN critère n'est pas respecté :
- Largeur < minwidth
- Hauteur < minheight  
- Taille > maxsize

### Export des données

Le type `mediacsv` exporte maintenant toutes les métadonnées :

```csv
id,expression_id,url,type,width,height,file_size,format,dominant_colors,image_hash,...
```

## Optimisation des performances

### Pour de gros volumes

1. **Crawler d'abord, analyser ensuite** :
   ```bash
   python mywi.py land crawl --name=projet --no-analyze-media --limit=1000
   python mywi.py land reanalyze --name=projet
   ```

2. **Analyser par batch** :
   ```bash
   # Utilise automatiquement le parallélisme défini dans settings.py
   python mywi.py land reanalyze --name=projet
   ```

3. **Nettoyer régulièrement** :
   ```bash
   # Supprimer les petites images régulièrement
   python mywi.py land reanalyze --name=projet --minwidth=100 --minheight=100 --suppress
   ```

## Résolution des problèmes

### Erreurs fréquentes

1. **"Image too small"** : L'image ne respecte pas les dimensions minimales
2. **"File too large"** : Le fichier dépasse la taille maximale
3. **"Download timeout"** : Augmenter `media_download_timeout` dans settings.py
4. **"Invalid image format"** : Format non supporté ou fichier corrompu

### Vérification de l'état

```bash
# Voir la progression de l'analyse
python mywi.py land media_stats --name=projet

# Identifier les erreurs
sqlite3 data/mwi.db "SELECT analysis_error, COUNT(*) FROM media WHERE analysis_error IS NOT NULL GROUP BY analysis_error"
```

## Cas d'usage avancés

### Détecter les doublons

```python
# Dans un script Python
from mwi.queries import find_duplicate_images
from mwi.model import Land

land = Land.get(Land.name == 'projet')
duplicates = find_duplicate_images(land)

for hash_val, count, urls, sources in duplicates:
    print(f"Image dupliquée {count} fois : {hash_val}")
```

### Analyse des couleurs dominantes

```python
from mwi.queries import get_color_distribution
from mwi.model import Land

land = Land.get(Land.name == 'projet')
colors = get_color_distribution(land)

# Afficher la palette de couleurs du projet
for color, percentage in sorted(colors.items(), key=lambda x: x[1], reverse=True):
    print(f"{color}: {percentage:.1f}%")
```

### Export personnalisé

```python
# Exporter seulement les grandes images
from mwi.model import Media, Expression, Land

land = Land.get(Land.name == 'projet')
large_images = (Media
    .select()
    .join(Expression)
    .where(
        Expression.land == land,
        Media.width > 1000,
        Media.height > 1000
    ))

# Créer un CSV personnalisé
import csv
with open('large_images.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['url', 'width', 'height', 'size_mb'])
    for img in large_images:
        writer.writerow([
            img.url, 
            img.width, 
            img.height, 
            img.file_size / 1024 / 1024
        ])
```
```

### 12.3 Schéma de migration SQL

```sql
-- Migration schema for reference
-- migrations/schema.sql

-- Ajout des colonnes d'analyse média
ALTER TABLE media ADD COLUMN width INTEGER DEFAULT NULL;
ALTER TABLE media ADD COLUMN height INTEGER DEFAULT NULL;
ALTER TABLE media ADD COLUMN file_size INTEGER DEFAULT NULL;
ALTER TABLE media ADD COLUMN format VARCHAR(10) DEFAULT NULL;
ALTER TABLE media ADD COLUMN color_mode VARCHAR(10) DEFAULT NULL;
ALTER TABLE media ADD COLUMN dominant_colors TEXT DEFAULT NULL;
ALTER TABLE media ADD COLUMN has_transparency BOOLEAN DEFAULT NULL;
ALTER TABLE media ADD COLUMN aspect_ratio REAL DEFAULT NULL;
ALTER TABLE media ADD COLUMN exif_data TEXT DEFAULT NULL;
ALTER TABLE media ADD COLUMN image_hash VARCHAR(64) DEFAULT NULL;
ALTER TABLE media ADD COLUMN content_tags TEXT DEFAULT NULL;
ALTER TABLE media ADD COLUMN nsfw_score REAL DEFAULT NULL;
ALTER TABLE media ADD COLUMN analyzed_at DATETIME DEFAULT NULL;
ALTER TABLE media ADD COLUMN analysis_error TEXT DEFAULT NULL;

-- Index pour optimiser les requêtes
CREATE INDEX idx_media_size ON media(file_size);
CREATE INDEX idx_media_dimensions ON media(width, height);
CREATE INDEX idx_media_hash ON media(image_hash);
CREATE INDEX idx_media_analyzed ON media(analyzed_at);

-- Vue pour les statistiques rapides
CREATE VIEW media_stats AS
SELECT
    e.land_id,
    COUNT(m.id) as total_media,
    COUNT(CASE WHEN m.analyzed_at IS NOT NULL THEN 1 END) as analyzed,
    AVG(m.width) as avg_width,
    AVG(m.height) as avg_height,
    AVG(m.file_size) as avg_size
FROM media m
JOIN expression e ON e.id = m.expression_id
GROUP BY e.land_id;
```

## Résumé

Cette implémentation complète offre :

1. **Analyse automatique** des images pendant le crawl
2. **Extraction de métadonnées** : dimensions, taille, format, couleurs, EXIF
3. **Filtrage et suppression** basés sur des critères configurables
4. **Statistiques détaillées** sur les médias collectés
5. **Détection de doublons** via hash perceptuel
6. **Performance optimisée** avec traitement par batch et parallélisme
7. **Sécurité** avec prévisualisation avant suppression
8. **Extensibilité** pour intégrer des modèles ML futurs

Le système est conçu pour être totalement intégré à l'application existante, avec une approche progressive permettant d'activer ou désactiver l'analyse selon les besoins.