# My Web Intelligence (MyWI)

MyWebIntelligence (MyWI) is a Python-based tool designed to assist researchers in digital humanities with creating and managing web-based research projects. It facilitates the collection, organization, and analysis of web data, storing information in a SQLite database. For browsing the database, a tool like [SQLiteBrowser](https://sqlitebrowser.org/) can be very helpful.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Using Docker](#using-docker)
  - [Local Development Setup](#local-development-setup)
- [Usage](#usage)
  - [General Notes](#general-notes)
  - [Land Management](#land-management)
  - [Data Collection](#data-collection)
  - [Domain Management](#domain-management)
  - [Exporting Data](#exporting-data)
  - [Heuristics](#heuristics)
- [Testing](#testing)
- [License](#license)

## Features

*   **Land Creation & Management**: Organize your research into "lands," which are thematic collections of terms and URLs.
*   **Web Crawling**: Crawl URLs associated with your lands to gather web page content.
*   **Content Extraction**: Process crawled pages to extract readable content.
*   **Domain Analysis**: Gather information about domains encountered during crawling.
*   **Data Export**: Export collected data in various formats (CSV, GEXF, raw corpus) for further analysis.
*   **Tag-based Analysis**: Export tag matrices and content for deeper insights.

---

## Architecture & Internals

### File Structure & Flow

```
mywi.py  →  mwi/cli.py  →  mwi/controller.py  →  mwi/core.py & mwi/export.py
                                     ↘︎ mwi/model.py (Peewee ORM)
```

- **mywi.py**: Console entry-point, runs CLI.
- **mwi/cli.py**: Parses CLI args, dispatches commands to controllers.
- **mwi/controller.py**: Maps verbs to business logic in core/export/model.
- **mwi/core.py**: Main algorithms (crawling, parsing, pipelines, scoring, etc.).
- **mwi/export.py**: Exporters (CSV, GEXF, corpus).
- **mwi/model.py**: Database schema (Peewee ORM).

### Database Schema (SQLite, via Peewee)

- **Land**: Research project/topic.
- **Word**: Normalized vocabulary.
- **LandDictionary**: Many-to-many Land/Word.
- **Domain**: Unique website/domain.
- **Expression**: Individual URL/page.
- **ExpressionLink**: Directed link between Expressions.
- **Media**: Images, videos, audio in Expressions.
- **Tag**: Hierarchical tags.
- **TaggedContent**: Snippets tagged in Expressions.

### Main Workflows

- **Project Bootstrap**: `python mywi.py db setup`
- **Land Life-Cycle**: Create, add terms, add URLs, crawl, extract readable, export, clean/delete.
- **Domain Processing**: `python mywi.py domain crawl`
- **Tag Export**: `python mywi.py tag export`
- **Heuristics Update**: `python mywi.py heuristic update`

### Implementation Notes

- **Relevance Score**: Weighted sum of lemma hits in title/content.
- **Async Batching**: Polite concurrency for crawling.
- **Media Extraction**: Only `.jpg` images kept, media saved for later download.
- **Export**: Multiple formats, dynamic SQL, GEXF with attributes.

### Settings

Key variables in `settings.py`:
- `data_location`, `user_agent`, `parallel_connections`, `default_timeout`, `archive`, `heuristics`.

### Testing

- `tests/test_cli.py`: CLI smoke tests.
- `tests/test_core.py`, etc.: Unit tests for extraction, parsing, export.

### Extending

- Add export: implement `Export.write_<type>`, update controller.
- Change language: pass `--lang` at land creation.
- Add headers/proxy: edit `settings` or patch session logic.
- Custom tags: use tag hierarchy, export flattens to paths.

---

## Installation

You can install MyWI using Docker (recommended for ease of use) or by setting up a local development environment.

### Using Docker

**Prerequisites:**
*   Python 3.10+ (for understanding the project, not strictly for running Docker if image is pre-built)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop)

**Steps:**

1.  **Create a Data Directory:**
    On your host machine, create a directory to store the SQLite database file and other persistent data. This directory will be mounted into the Docker container.
    ```bash
    mkdir ~/mywi_data 
    # Example: creates a directory named 'mywi_data' in your home folder
    ```

2.  **Clone the Project:**
    ```bash
    git clone https://github.com/MyWebIntelligence/MyWebIntelligencePython.git
    cd MyWebIntelligencePython
    ```

3.  **Configure Data Location:**
    Edit the `settings.py` file in the cloned project directory to specify the path *inside the container* where your host data directory will be mounted. The Docker run command (step 5) will map your host directory to `/data` inside the container by default.
    ```python
    # settings.py
    data_location = "/data" # This path is inside the container
    ```

4.  **Build the Docker Image:**
    ```bash
    docker build -t mwi:latest .
    # Using mwi:1.2 as per original, but latest is also common
    # docker build -t mwi:1.2 . 
    ```

5.  **Run the Docker Container:**
    Replace `/path/to/your/host/data` with the actual path to the data directory you created in step 1.
    ```bash
    docker run -dit --name mwi -v /path/to/your/host/data:/data mwi:latest
    # Example using the ~/mywi_data directory:
    # docker run -dit --name mwi -v ~/mywi_data:/data mwi:latest
    ```
    *   `-d`: Run in detached mode
    *   `-i`: Keep STDIN open even if not attached
    *   `-t`: Allocate a pseudo-TTY
    *   `--name mwi`: Assign a name to the container
    *   `-v /path/to/your/host/data:/data`: Mount your host data directory to `/data` inside the container.

6.  **Access the Container Shell:**
    ```bash
    docker exec -it mwi bash
    ```

7.  **Setup Database (inside the container):**
    If this is the first time, or if the database doesn't exist in your mounted volume:
    ```bash
    # Inside the Docker container
    python mywi.py db setup
    ```
    You are now ready to use MyWI commands as described in the [Usage](#usage) section.

### Local Development Setup

**Prerequisites:**
*   Python 3.10+
*   `pip` (Python package installer)
*   `virtualenv` (Python environment isolation tool)
*   `git`

**Steps:**

1.  **Install `virtualenv` (if not already installed):**
    ```bash
    pip install virtualenv
    ```

2.  **Clone the Project:**
    ```bash
    git clone https://github.com/MyWebIntelligence/MyWebIntelligencePython.git
    cd MyWebIntelligencePython
    ```

3.  **Create and Activate Virtual Environment:**

    *   **macOS / Linux:**
        ```bash
        virtualenv venv
        source venv/bin/activate
        ```
    *   **Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    Your command prompt should now be prefixed with `(venv)`.

4.  **Configure Data Location:**
    Create a data directory anywhere on your system. Then, edit the `settings.py` file in the project directory and update `data_location` to the absolute path of this directory.
    ```python
    # settings.py
    data_location = "/path/to/your/local/data" 
    # e.g., "C:/Users/YourUser/mywi_data" on Windows
    # or "/Users/youruser/mywi_data" on macOS/Linux
    ```

5.  **Install Dependencies:**
    ```bash
    (venv) pip install -r requirements.txt
    ```

6.  **Setup Database:**
    ```bash
    (venv) python mywi.py db setup
    ```
    This command creates the database file in the `data_location` you specified. Warning: it will destroy any previous data if the database file already exists from a prior setup.

You are now ready to use MyWI commands as described in the [Usage](#usage) section using `(venv) python mywi.py ...`.

## Usage

### General Notes

*   Commands are run using `python mywi.py ...`.
*   If using Docker, first execute `docker exec -it mwi bash` to enter the container. The prompt might be `root@<container_id>:/app#` or similar.
*   If using a local development setup, ensure your virtual environment is activated (e.g., `(venv)` prefix in your prompt).
*   Arguments like `LAND_NAME` or `TERMS` are placeholders; replace them with your actual values.

### Land Management

A "Land" is a central concept in MyWI, representing a specific research area or topic.

#### 1. Create a New Land

Create a new land (research topic/project).

```bash
python mywi.py land create --name="MyResearchTopic" --desc="A description of this research topic"
```

| Option      | Type   | Required | Default | Description                                 |
|-------------|--------|----------|---------|---------------------------------------------|
| --name      | str    | Yes      |         | Name of the land (unique identifier)        |
| --desc      | str    | No       |         | Description of the land                     |
| --lang      | str    | No       | fr      | Language code for the land (default: fr)    |

**Example:**
```bash
python mywi.py land create --name="AsthmaResearch" --desc="Research on asthma and air quality" --lang="en"
```

---

#### 2. List Created Lands

List all lands or show properties of a specific land.

- List all lands:
  ```bash
  python mywi.py land list
  ```
- Show details for a specific land:
  ```bash
  python mywi.py land list --name="MyResearchTopic"
  ```

| Option   | Type | Required | Default | Description                      |
|----------|------|----------|---------|----------------------------------|
| --name   | str  | No       |         | Name of the land to show details |

---

#### 3. Add Terms to a Land

Add keywords or phrases to a land.

```bash
python mywi.py land addterm --land="MyResearchTopic" --terms="keyword1, keyword2, related phrase"
```

| Option   | Type | Required | Default | Description                                 |
|----------|------|----------|---------|---------------------------------------------|
| --land   | str  | Yes      |         | Name of the land to add terms to            |
| --terms  | str  | Yes      |         | Comma-separated list of terms/keywords      |

---

#### 4. Add URLs to a Land

Add URLs to a land, either directly or from a file.

- Directly:
  ```bash
  python mywi.py land addurl --land="MyResearchTopic" --urls="https://example.com/page1, https://anothersite.org/article"
  ```
- From a file (one URL per line):
  ```bash
  python mywi.py land addurl --land="MyResearchTopic" --path="/path/to/your/url_list.txt"
  ```
  *(If using Docker, ensure this file is accessible within the container, e.g., in your mounted data volume.)*

| Option   | Type | Required | Default | Description                                 |
|----------|------|----------|---------|---------------------------------------------|
| --land   | str  | Yes      |         | Name of the land to add URLs to             |
| --urls   | str  | No       |         | Comma-separated list of URLs to add         |
| --path   | str  | No       |         | Path to a file containing URLs (one per line) |

---

#### 5. Delete a Land or Expressions

Delete an entire land or only expressions below a relevance threshold.

- Delete an entire land:
  ```bash
  python mywi.py land delete --name="MyResearchTopic"
  ```
- Delete expressions with relevance lower than a specific value:
  ```bash
  python mywi.py land delete --name="MyResearchTopic" --maxrel=MAXIMUM_RELEVANCE
  # e.g., --maxrel=0.5
  ```

| Option   | Type   | Required | Default | Description                                         |
|----------|--------|----------|---------|-----------------------------------------------------|
| --name   | str    | Yes      |         | Name of the land to delete                          |
| --maxrel | float  | No       |         | Only delete expressions with relevance < maxrel      |


### Data Collection

#### 1. Crawl Land URLs

Crawl the URLs added to a land to fetch their content.

```bash
python mywi.py land crawl --name="MyResearchTopic" [--limit=NUMBER] [--http=HTTP_STATUS_CODE]
```

| Option   | Type   | Required | Default | Description                                                                 |
|----------|--------|----------|---------|-----------------------------------------------------------------------------|
| --name   | str    | Yes      |         | Name of the land whose URLs to crawl                                        |
| --limit  | int    | No       |         | Maximum number of URLs to crawl in this run                                 |
| --http   | str    | No       |         | Re-crawl only pages that previously resulted in this HTTP error (e.g., 503) |

**Examples:**
```bash
python mywi.py land crawl --name="AsthmaResearch"
python mywi.py land crawl --name="AsthmaResearch" --limit=10
python mywi.py land crawl --name="AsthmaResearch" --http=503
```

---

#### 2. Fetch Readable Content

Extract a cleaner, more readable version of the crawled page content (requires Mercury Parser CLI).

```bash
python mywi.py land readable --name="MyResearchTopic" [--limit=NUMBER]
```

| Option   | Type   | Required | Default | Description                                         |
|----------|--------|----------|---------|-----------------------------------------------------|
| --name   | str    | Yes      |         | Name of the land to process                         |
| --limit  | int    | No       |         | Maximum number of pages to process in this run      |

**Examples:**
```bash
python mywi.py land readable --name="AsthmaResearch"
python mywi.py land readable --name="AsthmaResearch" --limit=20
```

### Domain Management

#### 1. Crawl Domains

Get information from domains that were identified from expressions added to lands.

```bash
python mywi.py domain crawl [--limit=NUMBER] [--http=HTTP_STATUS_CODE]
```

| Option   | Type   | Required | Default | Description                                                                 |
|----------|--------|----------|---------|-----------------------------------------------------------------------------|
| --limit  | int    | No       |         | Maximum number of domains to crawl in this run                              |
| --http   | str    | No       |         | Re-crawl only domains that previously resulted in this HTTP error (e.g., 503) |

**Examples:**
```bash
python mywi.py domain crawl
python mywi.py domain crawl --limit=5
python mywi.py domain crawl --http=404
```

---

### Exporting Data

Export data from your lands or tags for analysis in other tools.

#### 1. Export Land Data

Export data from a land in various formats.

```bash
python mywi.py land export --name="MyResearchTopic" --type=EXPORT_TYPE [--minrel=MINIMUM_RELEVANCE]
```

| Option   | Type   | Required | Default | Description                                                                 |
|----------|--------|----------|---------|-----------------------------------------------------------------------------|
| --name   | str    | Yes      |         | Name of the land to export                                                  |
| --type   | str    | Yes      |         | Export type (see below)                                                     |
| --minrel | float  | No       |         | Minimum relevance for expressions to be included in the export              |

**EXPORT_TYPE values:**
- `pagecsv`: CSV of pages
- `pagegexf`: GEXF graph of pages
- `fullpagecsv`: CSV with full page content
- `nodecsv`: CSV of nodes
- `nodegexf`: GEXF graph of nodes
- `mediacsv`: CSV of media links
- `corpus`: Raw text corpus

**Examples:**
```bash
python mywi.py land export --name="AsthmaResearch" --type=pagecsv
python mywi.py land export --name="AsthmaResearch" --type=corpus --minrel=0.7
```

---

#### 2. Export Tag Data

Export tag-based data for a land.

```bash
python mywi.py tag export --name="MyResearchTopic" --type=EXPORT_TYPE [--minrel=MINIMUM_RELEVANCE]
```

| Option   | Type   | Required | Default | Description                                                                 |
|----------|--------|----------|---------|-----------------------------------------------------------------------------|
| --name   | str    | Yes      |         | Name of the land whose tags to export                                       |
| --type   | str    | Yes      |         | Export type (see below)                                                     |
| --minrel | float  | No       |         | Minimum relevance for tag content to be included in the export              |

**EXPORT_TYPE values:**
- `matrix`: Tag co-occurrence matrix
- `content`: Content associated with tags

**Examples:**
```bash
python mywi.py tag export --name="AsthmaResearch" --type=matrix
python mywi.py tag export --name="AsthmaResearch" --type=content --minrel=0.5
```

---

### Heuristics

#### 1. Update Domains from Heuristic Settings

Update domain information based on predefined or learned heuristics.

```bash
python mywi.py heuristic update
```

_No options for this command._


## Testing

To run tests for the project:
```bash
pytest tests/
```
To run a specific test file:
```bash
pytest tests/test_cli.py
```
To run a specific test method within a file:
```bash
pytest tests/test_cli.py::test_functional_test
```

## License

This project is licensed under the terms of the LICENSE file. (Assuming a LICENSE file exists in the repository, e.g., MIT, Apache 2.0).
If `LICENSE` is the actual name of the file, you can link to it: [LICENSE](LICENSE).
