# My Web Intelligence

MyWebIntelligence is a tool to create projects for research in digital humanities.
A Sqlite database browser like https://sqlitebrowser.org/ may be useful.

# Install from Docker

## Requirements

* Python 3.10
* [Docker](https://www.docker.com/products/docker-desktop)

## Installation

On your host machine, create a directory to store database file and other persistent data.
This directory will be further mounted in Docker container.

Clone project
 
```bash
$ git clone https://github.com/MyWebIntelligence/MyWebIntelligencePython.git
```

Inside project directory, edit your local (and persistent) data directory in `settings.py` file 

```python
data_location = "/path/to/hosted/data"
```

Then build Docker image

```bash
$ docker build -t mwi:1.2 .
```

Then run image with mounted data directory

```bash
$ docker run -dit --name mwi -v /path/to/hosted/data:/data mwi:1.2
```

Next, execute interactive shell on the container

```bash
$ docker exec -it mwi bash
``` 

Create database if it does not exist

```
# python mywi.py db setup
```

Or use commands described in [Usage](#usage)

# Usage

## Enter in Docker Container

Execute interactive shell on the container

```bash
$ docker exec -it mwi bash
``` 

## Lands

### Create new land

```bash
[venv/bin/]$ python mywi.py land create --name=LAND_NAME --desc=LAND_DESCRIPTION
```

### List created lands

Optional name to get properties of one land

```bash
[venv/bin/]$ python mywi.py land list [--name=LAND_NAME]
```

### Add terms to land

Terms argument is a quoted list of comma separated words `--terms="asthma, asthmatic, William Turner"`

```bash
[venv/bin/]$ python mywi.py land addterm --land=LAND_NAME --terms=TERMS
```

### Add url to land

Urls argument is a quoted list of URL, space or comma separated `--urls="https://domain1.com/page1.html, https://domain2.com/page2.html"`.
Path argument must point to a file containing one URL per line, file extension doesn't matter `--path=data/url_list.txt`.

```bash
[venv/bin/]$ python mywi.py land addurl --land=LAND_NAME [--urls=URLS | --path=PATH]
```

### Delete land

Set optional maxrel parameter to only delete expressions with relevance lower than MAXIMUM_RELEVANCE 

```bash
[venv/bin/]$ python mywi.py land delete --name=LAND_NAME [--maxrel=MAXIMUM_RELEVANCE]
```

### Crawl land urls

Start crawling URLs. Each level of depth are processed separately. The number of URLs to crawl can be set with `--limit` argument.
To re crawl pages in error (503 for example), set the http status code with `--http`.

```bash
[venv/bin/]$ python mywi.py land crawl --name=LAND_NAME [--limit=LIMIT, --http=HTTP_STATUS]
```

### Fetch land readable

Get land expressions readable from Mercury Parser if installed.
To install Mercury Parser with CLI binary :
```bash
$ yarn global add @postlight/mercury-parser
``` 

```bash
[venv/bin/]$ python mywi.py land readable --name=LAND_NAME [--limit=LIMIT]
```

### Crawl domains

Get info from domains created after expression addition.
To re crawl domains in error (503 for example), set the http status code with `--http`.

```bash
[venv/bin/]$ python mywi.py domain crawl [--limit=LIMIT, --http=HTTP_STATUS]
```

### Export land

type = ['pagecsv', 'pagegexf', 'fullpagecsv', 'nodecsv', 'nodegexf', 'mediacsv', 'corpus']

```bash
[venv/bin/]$ python mywi.py land export --name=LAND_NAME --type=EXPORT_TYPE --minrel=MINIMUM_RELEVANCE
```

### Export tags

type = ['matrix', 'content']

```bash
[venv/bin/]$ python mywi.py tag export --name=LAND_NAME --type=EXPORT_TYPE --minrel=MINIMUM_RELEVANCE
```

### Update domains from heuristic settings

```bash
[venv/bin/]$ python mywi.py heuristic update
```

# Install development environment

## Prerequisites (Python+Pip+Virtualenv+Git)

Install python (on Windows https://www.python.org/downloads/release/python-374/) and/or pip (on windows https://pip.pypa.io/en/stable/installing/) if needed

Install virtualenv (https://virtualenv.pypa.io/en/stable/userguide/) if needed

```bash
$ pip install virtualenv
```

Install the git My Web intelligence Repository (on windows https://git-scm.com/ AND https://www.atlassian.com/git/tutorials/install-git#windows)

```bash
$ git clone https://github.com/MyWebIntelligence/MyWebIntelligencePython.git
```


## Activate your Virtual Environment

Change to application directory, create virtual env then activate
AND
Inside project directory, edit your local (and persistent) data directory in `settings.py` file 

```python
data_location = "/path/to/hosted/data"
```


FOR MAC

Create an instance in the current directory
```bash
$ virtualenv venv
```
Activate your virtual env
```bash
$ source venv/bin/activate
```

FOR WINDOWS
Create an instance in the current directory
```bash
$ python -m venv C:\Users\some_user\project_folder\venv
```

Activate your virtual env
```bash
C:\Users\some_user\project_folder> venv\Scripts\activate
```

## Install dependencies

```bash
 [venv/bin/MyWebIntelligencePython]$ pip install -r requirements.txt

```

## Setup Database

```bash
[venv/bin/]$ python mywi.py db setup
```
Create database (warning, destroys any previous data). 

# Tests

```
> pytest tests/<testfile.py>[::<test_method>]
```

Example testing unique method :

`pytest tests/test_cli.py::test_functional_test`

