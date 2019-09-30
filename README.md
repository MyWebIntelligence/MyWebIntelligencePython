# My Web Intelligence

MyWebIntelligence is a tool to create projects for research in digital humanities.
A Sqlite database browser like https://sqlitebrowser.org/ may be useful.

## Prerequisit (Python+Pip+Virtualenv+Git)

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
 [venv/bin/]$ pip install -r requirements.txt
```

## Setup Database

```bash
[venv/bin/]$ python mywi.py db setup
```

# Lands
## RE-Activate your Virtual Environment

Change to application directory and activate venv

```bash
$ source venv/bin/activate
```

For Windows

```bash
C:\Users\some_user\project_folder> venv\Scripts\activate
```

## Create new land

```bash
[venv/bin/]$ python mywi.py land create --name=LAND_NAME --desc=LAND_DESCRIPTION
```

## List created lands

```bash
[venv/bin/]$ python mywi.py land list
```

## Add terms to land

Terms argument is a quoted list of comma separated words `--terms="asthma, asthmatic, William Turner"`

```bash
[venv/bin/]$ python mywi.py land addterm --land=LAND_NAME --terms=TERMS
```

## Add url to land

Urls argument is a quoted list of URL, space or comma separated `--urls="https://domain1.com/page1.html, https://domain2.com/page2.html"`.
Path argument must point to a file containing one URL per line, file extension doesn't matter `--path=data/url_list.txt`.

```bash
[venv/bin/]$ python mywi.py land addurl --land=LAND_NAME [--urls=URLS | --path=PATH]
```

## Delete land

```bash
[venv/bin/]$ python mywi.py land delete --name=LAND_NAME
```

## Crawl land urls

Start crawling URLs. Each level of depth are processed separately. The number of URLs to crawl can be set with `--limit` argument.
To re crawl pages in error (503 for example), set the http status code with `--http`.

```bash
[venv/bin/]$ python mywi.py land crawl --name=LAND_NAME [--limit=LIMIT, --http=HTTP_STATUS]
```

## Export land

type = ['pagecsv', 'pagegexf', 'fullpagecsv', 'nodecsv', 'nodegexf', 'mediacsv']

```bash
[venv/bin/]$ python mywi.py land export --name=LAND_NAME --type=EXPORT_TYPE --minrel=MINIMUM_RELEVANCE
```

## Print land properties

```bash
[venv/bin/]$ python mywi.py land properties --name=LAND_NAME
```

## Crawl domains

Get info from domains created after expression addition.
To re crawl domains in error (503 for example), set the http status code with `--http`.

```bash
[venv/bin/]$ python mywi.py domain crawl [--limit=LIMIT, --http=HTTP_STATUS]
```

## Update domains from heuristic settings

```bash
[venv/bin/]$ python mywi.py heuristic update
```
