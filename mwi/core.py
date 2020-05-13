"""
Core functions
"""
import re
from typing import Union
from argparse import Namespace
from urllib.parse import urlparse
import requests
import aiohttp
import asyncio
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import FrenchStemmer
from bs4 import BeautifulSoup
from peewee import IntegrityError, JOIN
import settings
from . import model
from .export import Export

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


def confirm(message: str) -> bool:
    """
    Confirms action by requesting right input from user
    :param message:
    :return:
    """
    return input(message) == 'Y'


def check_args(args: Namespace, mandatory) -> bool:
    """
    Returns True if all required args are in parsed input args
    :param args:
    :param mandatory:
    :return:
    """
    args = vars(args)
    if isinstance(mandatory, str):
        mandatory = [mandatory]
    for arg in mandatory:
        if arg not in args or args[arg] is None:
            raise ValueError('Argument "%s" is required' % arg)
    return True


def split_arg(arg: str) -> list:
    """
    Splits arg string using comma separator and returns a filtered list
    :param arg:
    :return:
    """
    args = arg.split(",")
    return [a.strip() for a in args if a]


def get_arg_option(name: str, args: Namespace, set_type, default):
    """
    Returns value from optional argument
    :param name:
    :param args:
    :param set_type:
    :param default:
    :return:
    """
    args = vars(args)
    if (name in args) and (args[name] is not None):
        return set_type(args[name])
    return default


def stem_word(word: str) -> str:
    """
    Stems word with NLTK Snowball FrenchStemmer
    :param word:
    :return:
    """
    if 'stemmer' not in stem_word.__dict__:
        stem_word.stemmer = FrenchStemmer()
    return stem_word.stemmer.stem(word.lower())


def crawl_domains(limit: int = 0, http: str = None):
    """
    Crawl domains to retrieve info
    :param limit:
    :param http:
    :return:
    """
    domains = model.Domain.select()
    if limit > 0:
        domains = domains.limit(limit)
    if http is not None:
        domains = domains.where(model.Domain.http_status == http)
    else:
        domains = domains.where(model.Domain.fetched_at.is_null())
    processed = 0
    for domain in domains:
        try:
            try:
                request = requests.get(
                    "https://%s" % domain.name,
                    headers={"User-Agent": settings.user_agent},
                    timeout=5)
            except Exception as exception:
                request = requests.get(
                    "http://%s" % domain.name,
                    headers={"User-Agent": settings.user_agent},
                    timeout=5)
            domain.http_status = request.status_code
            domain.fetched_at = model.datetime.datetime.now()
            if ('html' in request.headers['content-type']) and (request.status_code == 200):
                process_domain_content(domain, request.text)
                processed += 1
        except Exception as exception:
            print(exception)
            domain.fetched_at = model.datetime.datetime.now()
        domain.save()
    return processed


def process_domain_content(domain: model.Domain, html: str):
    """
    Process domain info from HTML
    :param domain:
    :param html:
    :return:
    """
    soup = BeautifulSoup(html, 'html.parser')
    domain.title = soup.title.string.strip()
    domain.description = get_meta_content(soup, 'description')
    domain.keywords = get_meta_content(soup, 'keywords')


def get_meta_content(soup: BeautifulSoup, name: str):
    """
    Get named meta content property
    :param soup:
    :param name:
    :return:
    """
    tag = soup.find('meta', attrs={'name': name})
    return tag['content'] if (tag and 'content' in tag) else ''


async def crawl_land(land: model.Land, limit: int = 0, http: str = None) -> tuple:
    """
    Start land crawl
    :param land:
    :param limit:
    :param http:
    :return:
    """
    print("Crawling land %d" % land.id)
    expressions = model.Expression.select()
    if limit > 0:
        expressions = expressions.limit(limit)
    if http is not None:
        expressions = expressions.where(
            model.Expression.land == land,
            model.Expression.http_status == http)
    else:
        expressions = expressions.where(
            model.Expression.land == land,
            model.Expression.fetched_at.is_null())
    expressions = expressions.order_by(model.Expression.depth)

    connector = aiohttp.TCPConnector(limit=settings.parallel_connections, verify_ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for expression in list(expressions):
            tasks.append(crawl_expression(expression, session))

        results = await asyncio.gather(*tasks)
        return expressions.count(), expressions.count() - sum(results)


async def crawl_expression(expression, session):
    print("Crawling %s" % expression.url)
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
                process_expression_content(expression, content)
                result = 1
            expression.save()
            return result
    except Exception:
        expression.save()
        return result


def add_expression(land: model.Land, url: str, depth=0) -> Union[model.Expression, bool]:
    """
    Add expression to land
    :param land:
    :param url:
    :param depth:
    :return:
    """
    url = remove_anchor(url)
    if is_crawlable(url):
        domain_name = get_domain_name(url)
        domain = model.Domain.get_or_create(name=domain_name)[0]
        expression = model.Expression.get_or_none(model.Expression.url == url, model.Expression.land == land)
        if expression is None:
            expression = model.Expression.create(land=land, domain=domain, url=url, depth=depth)
        return expression
    return False


def get_domain_name(url: str) -> str:
    """
    Returns domain from any url as sub.domain.ext or according to heuristics settings
    :param url:
    :return:
    """
    parsed = urlparse(url)
    domain_name = parsed.netloc
    for key, value in settings.heuristics.items():
        if domain_name.endswith(key):
            matches = re.findall(value, url)
            domain_name = matches[0] if matches else domain_name
    return domain_name


def remove_anchor(url: str) -> str:
    """
    Removes anchor from URL
    :param url:
    :return:
    """
    anchor_pos = url.find('#')
    return url[:anchor_pos] if anchor_pos > 0 else url


def link_expression(land: model.Land, source_expression: model.Expression, url: str) -> bool:
    """
    Link target expression to source expression
    :param land:
    :param source_expression:
    :param url:
    :return:
    """
    with model.DB.atomic():
        target_expression = add_expression(land, url, source_expression.depth + 1)
        if target_expression:
            try:
                model.ExpressionLink.create(
                    source_id=source_expression.get_id(),
                    target_id=target_expression.get_id())
                return True
            except IntegrityError:
                pass
    return False


def is_crawlable(url: str):
    """
    Checks whether an URL is valid for crawling
    :param url:
    :return:
    """
    try:
        parsed = urlparse(url)
        exclude_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.pdf',
                       '.txt', '.csv', '.xls', '.xlsx', '.doc', '.docx')

        return \
            (url is not None) \
            and (parsed.path not in (None, '', '/')) \
            and url.startswith(('http://', 'https://')) \
            and (not url.endswith(exclude_ext))
    except:
        return False


def process_expression_content(expression: model.Expression, html: str) -> model.Expression:
    """
    Process expression fields from HTML content
    :param expression:
    :param html:
    :return:
    """
    soup = BeautifulSoup(html, 'html.parser')
    words = get_land_dictionary(expression.land)

    if soup.html is not None:
        expression.lang = soup.html.get('lang', '')
    if soup.title is not None:
        expression.title = soup.title.string.strip()
    expression.description = get_meta_content(soup, 'description')
    expression.keywords = get_meta_content(soup, 'keywords')

    clean_html(soup)

    if settings.archive is True:
        path = 'data/lands/%s/%s' % (expression.land.get_id(), expression.get_id())
        with open(path, 'w', encoding="utf-8") as html_file:
            html_file.write(html.strip())
        html_file.close()

    expression.readable = get_readable(soup)
    expression.relevance = expression_relevance(words, expression)

    if expression.relevance > 0:
        print("Expression #%d approved" % expression.get_id())
        extract_medias(soup, expression)
        expression.approved_at = model.datetime.datetime.now()
        if expression.depth < 3:
            urls = [a.get('href') for a in soup.find_all('a') if is_crawlable(a.get('href'))]
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def extract_medias(content, expression):
    """
    Extract media src (img, video) from html content
    :param content:
    :param expression:
    :return:
    """
    medias = []
    for tag in ['img', 'video', 'audio']:
        for element in content.find_all(tag):
            src = element.get('src')
            is_valid_src = src is not None and src not in medias
            if tag == 'img':
                is_valid_src = is_valid_src and src.endswith(".jpg")
            if is_valid_src:
                if src.startswith("/"):
                    src = expression.url[:expression.url.find("/", 9) + 1].strip('/') + src
                media = model.Media.create(expression=expression, url=src, type=tag)
                media.save()


def get_readable(content):
    """
    Get readable part of HTML content
    :param content:
    :return:
    """
    text = content.get_text(separator=' ')
    lines = text.split("\n")
    text_lines = [l.strip() for l in lines if len(l.strip()) > 0]
    return "\n".join(text_lines)


def clean_html(soup):
    """
    Get rid of DOM objects with no valuable content
    :param soup:
    :return:
    """
    remove_selectors = ('script', 'style', 'iframe', 'form', 'footer', '.footer',
                        'nav', '.nav', '.menu', '.social', '.modal')
    for selector in remove_selectors:
        for tag in soup.select(selector):
            tag.decompose()


def get_land_dictionary(land: model.Land):
    """
    Get land dictionary
    :param land:
    :return:
    """
    return model.Word.select() \
        .join(model.LandDictionary, JOIN.LEFT_OUTER) \
        .where(model.LandDictionary.land == land)


def land_relevance(land: model.Land):
    """
    Start relevance computing according to land dictionary for each expression in land
    :param land:
    :return:
    """
    words = get_land_dictionary(land)
    select = model.Expression.select() \
        .where(model.Expression.land == land, model.Expression.readable.is_null(False))
    row_count = select.count()
    if row_count > 0:
        print("Updating relevances for %d expressions, it may take some time." % row_count)
        for expression in select:
            expression.relevance = expression_relevance(words, expression)
            expression.save()


def expression_relevance(dictionary, expression: model.Expression) -> int:
    """
    Compute expression relevance according to land dictionary
    :param dictionary:
    :param expression:
    :return:
    """
    lemmas = [w.lemma for w in dictionary]
    occurrences = []
    try:
        content = [stem_word(w) for w in word_tokenize(expression.readable, language='french')]
        content = " ".join(content)
        occurrences = [content.count(lemma) for lemma in lemmas]
    except:
        pass
    return sum(occurrences)


def export_land(land: model.Land, export_type: str, minimum_relevance: int):
    """
    Export land data
    :param land:
    :param export_type:
    :param minimum_relevance:
    :return:
    """
    date_tag = model.datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = 'data/export_%s_%s_%s' % (land.name, export_type, date_tag)
    export = Export(export_type, land, minimum_relevance)
    count = export.write(export_type, filename)
    if count > 0:
        print("Successfully exported %s records to %s" % (count, filename))
    else:
        print("No records to export, check crawling state or lower minimum relevance threshold")


def update_heuristic():
    """
    Update domains according to heuristic settings
    :return:
    """
    domains = list(model.Domain.select().dicts())
    domains = {x['id']: x for x in domains}
    expressions = model.Expression.select()
    updated = 0
    for expression in expressions:
        domain = get_domain_name(expression.url)
        if domain != domains[expression.domain_id]['name']:
            to_domain, _ = model.Domain.get_or_create(name=domain)
            expression.domain = to_domain
            expression.save()
            updated += 1
    print("%d domain(s) updated" % updated)
