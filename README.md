# My Web Intelligence

## Activate your Virtual Environment

Install virtualenv if needed

```bash
$ pip install virtualenv
```

Change to application directory, create virtual env then activate

```bash
$ virtualenv venv
```

```bash
$ source venv/bin/activate
```

For Windows

```bash
C:\Users\some_user\project_folder> venv\Scripts\activate
```

## Install dependencies

```bash
$ pip install -r requirements.txt
```

## Setup Database

```bash
$ python mywi.py db setup
```

# Lands

## Create new land

```bash
$ python mywi.py land create --name=LAND_NAME --desc=LAND_DESCRIPTION
```

## List created lands

```bash
$ python mywi.py land list
```

## Add terms to land

```bash
$ python mywi.py land addterm --land=LAND_NAME --terms=TERMS
```

## Add url to land

```bash
$ python mywi.py land addurl --land [--urls=URLS | --path=PATH]
```

## Delete land

```bash
$ python mywi.py land delete --name=LAND_NAME
```

## Crawl land urls

```bash
$ python mywi.py land crawl --name=LAND_NAME
```

## Export land

```bash
$ python mywi.py land export --name=LAND_NAME
```

## Print land properties

```bash
$ python mywi.py land properties --name=LAND_NAME
```
