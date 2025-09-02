# CLAUDE.md

## Table of Contents
- [Project Overview](#project-overview)
- [Development Commands](#development-commands)
- [Domain & Media Operations](#domain--media-operations)
- [Architecture](#architecture)
  - [Core Components](#core-components)
  - [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Development Notes](#development-notes)
- [Testing](#testing)
- [Installation Requirements](#installation-requirements)
- [Docker Setup](#docker-setup)
- [Export Formats](#export-formats)
  - [Land Exports](#land-exports)
  - [Tag Exports](#tag-exports)

## Project Overview

MyWebIntelligence (MyWI) is a Python-based web intelligence tool for digital humanities researchers. It helps collect, organize, and analyze web data using a SQLite database with a focus on research project management through "lands" (thematic collections).

## Development Commands

### Testing

| Command                                      | Description                     |
|----------------------------------------------|---------------------------------|
| `pytest tests/`                              | Run all tests                   |
| `pytest tests/test_cli.py`                   | Run specific test file          |
| `pytest tests/test_cli.py::test_functional_test` | Run specific test method        |

### Database Management

| Command                                      | Description                     |
|----------------------------------------------|---------------------------------|
| `python mywi.py db setup`                    | Create database schema (destructive) |
| `python mywi.py db migrate`                  | Run database migrations         |

### Land Management

| Command                                      | Description                     |
|----------------------------------------------|---------------------------------|
| `python mywi.py land create --name="ResearchTopic" --desc="Description" --lang="fr"` | Create a new research land      |
| `python mywi.py land list`                    | List all lands                  |
| `python mywi.py land addterm --land="ResearchTopic" --terms="keyword1, keyword2"` | Add terms to land dictionary    |
| `python mywi.py land addurl --land="ResearchTopic" --urls="https://example.com"` | Add URLs to land                |
| `python mywi.py land crawl --name="ResearchTopic"` | Crawl land URLs                |
| `python mywi.py land readable --name="ResearchTopic" --merge=smart_merge` | Extract readable content using Mercury Parser |
| `python mywi.py land consolidate --name="ResearchTopic"` | Consolidate land (repair links and media after external modifications) |
| `python mywi.py land export --name="ResearchTopic" --type=pagecsv` | Export land data               |
| `python mywi.py land medianalyse --name="ResearchTopic"` | Analyze media in land          |

### Domain & Media Operations

| Command                                      | Description                     |
|----------------------------------------------|---------------------------------|
| `python mywi.py domain crawl`                | Crawl domains                  |
| `python mywi.py tag export --name="ResearchTopic" --type=matrix` | Export tags                   |
| `python mywi.py heuristic update`            | Update heuristics              |

## Architecture

#### Core Components
- **mywi.py**: Entry point that invokes CLI
- **mwi/cli.py**: Command-line interface parser and dispatcher
- **mwi/controller.py**: Controllers mapping verbs to business logic
- **mwi/core.py**: Core algorithms (crawling, parsing, scoring)
- **mwi/export.py**: Data export functionality
- **mwi/model.py**: Database schema using Peewee ORM
- **mwi/media_analyzer.py**: Media analysis with color extraction and metadata
- **mwi/readable_pipeline.py**: Mercury Parser integration for content extraction

#### Database Schema
- **Land**: Research projects/topics
- **Expression**: Individual URLs/pages with relevance scoring
- **ExpressionLink**: Directed links between expressions
- **Word**: Normalized vocabulary with lemmatization
- **LandDictionary**: Many-to-many relationship between lands and words
- **Domain**: Unique websites/domains
- **Media**: Images, videos, audio with analysis metadata
- **Tag**: Hierarchical tagging system
- **TaggedContent**: Content snippets associated with tags

### Key Features
- **Relevance Scoring**: Weighted sum of lemma hits in title/content
- **Async Processing**: Polite concurrency for web crawling
- **Media Analysis**: Automatic extraction with color analysis, EXIF data, and perceptual hashing
- **Mercury Parser Integration**: High-quality content extraction with merge strategies
- **Dynamic Media Extraction**: Playwright-based extraction for JavaScript-generated content
- **Link Graph Construction**: Automatic link discovery and relationship mapping

## Configuration

### Settings (settings.py)
- `data_location`: Directory for database and files
- `user_agent`: HTTP user agent string
- `parallel_connections`: Concurrent connection limit
- `default_timeout`: Network request timeout
- `dynamic_media_extraction`: Enable/disable headless browser media extraction
- `media_*`: Media analysis configuration (dimensions, file size, colors)
- `heuristics`: Domain-specific URL patterns for social media extraction

### Dependencies
- **Core**: aiohttp, beautifulsoup4, nltk, peewee, trafilatura
- **Media**: Pillow, numpy, scikit-learn, imagehash
- **Browser**: playwright (optional for dynamic media extraction)
- **Testing**: pytest

## Development Notes

### Mercury Parser Pipeline
The readable pipeline uses Mercury Parser for content extraction with configurable merge strategies:
- `smart_merge`: Intelligent fusion based on field type (default)
- `mercury_priority`: Mercury always overwrites existing data
- `preserve_existing`: Only fills empty fields

### Media Analysis
- Supports images, videos, and audio
- Extracts metadata (dimensions, format, colors, EXIF)
- Uses perceptual hashing for duplicate detection
- Configurable size and quality filters

### Language Support
- Default language: French (`fr`)
- Uses NLTK for tokenization and French stemming
- Supports multiple languages via `--lang` parameter

### Async Operations
- Uses asyncio for concurrent web operations
- Windows requires ProactorEventLoop
- Configurable connection limits and timeouts

## Testing

The project includes comprehensive tests covering:
- CLI functionality (`tests/test_cli.py`)
- Core algorithms (`tests/test_core.py`)
- Metadata extraction (`tests/test_metadata*.py`)
- Expression handling (`tests/test_expression_metadata.py`)

## Installation Requirements

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Optional: Install Playwright for dynamic media extraction
python install_playwright.py
```

### Docker Setup
```bash
# Build image
docker build -t mwi:latest .

# Run container with data volume
docker run -dit --name mwi -v /path/to/data:/data mwi:latest
```

## Export Formats

#### Land Exports
- `pagecsv`: CSV of pages with metadata
- `fullpagecsv`: CSV with full page content
- `pagegexf`: GEXF graph format for network analysis
- `nodecsv`: CSV of nodes
- `nodegexf`: GEXF graph of nodes
- `mediacsv`: CSV of media links
- `corpus`: Raw text corpus

#### Tag Exports
- `matrix`: Tag co-occurrence matrix
- `content`: Content associated with tags
