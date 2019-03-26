# My Web Intelligence

## Activate your Virtual Environment

## Install dependencies

## Setup Database

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
