"""
Core functions
"""
from .model import *
from .export import Export
import settings
import re
import requests
from argparse import Namespace
from urllib.parse import urlparse
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import FrenchStemmer
from bs4 import BeautifulSoup


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
    Splits arg string using [, ] separators and returns a filtered list
    :param arg:
    :return:
    """
    args = re.split('[, ]', arg)
    return [a for a in args if a]


def get_arg_option(name: str, args: Namespace, typeof, default):
    """
    Returns value from optional argument "limit"
    :param name:
    :param args:
    :param typeof:
    :param default:
    :return:
    """
    args = vars(args)
    if (name in args) and (args[name] is not None):
        if default is not None:
            value = default
        value = typeof(args[name])
        return value
    else:
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
    domains = Domain.select()
    if limit > 0:
        domains = domains.limit(limit)
    if http is not None:
        domains = domains.where(Domain.http_status == http)
    else:
        domains = domains.where(Domain.fetched_at.is_null())
    processed = 0
    for domain in domains:
        try:
            try:
                r = requests.get("https://%s" % domain.name, timeout=5)
            except Exception as e:
                r = requests.get("http://%s" % domain.name, timeout=5)
            domain.http_status = r.status_code
            domain.fetched_at = datetime.datetime.now()
            if ('html' in r.headers['content-type']) and (r.status_code == 200):
                process_domain_content(domain, r.text)
                processed += 1
        except Exception as e:
            print(e)
            domain.fetched_at = datetime.datetime.now()
        domain.save()
    return processed


def process_domain_content(domain: Domain, html: str):
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
    return tag['content'] if tag else ''


def crawl_land(land: Land, limit: int = 0, http: str = None) -> tuple:
    """
    Start land crawl
    :param land:
    :param limit:
    :param http:
    :return:
    """
    expressions = Expression.select()
    if limit > 0:
        expressions = expressions.limit(limit)
    if http is not None:
        expressions = expressions.where(Expression.land == land, Expression.http_status == http)
    else:
        expressions = expressions.where(Expression.land == land, Expression.fetched_at.is_null())
    expressions = expressions.order_by(Expression.depth)

    processed = 0
    errors = 0
    for expression in list(expressions):
        try:
            r = requests.get(expression.url, timeout=5)
            expression.http_status = r.status_code
            expression.fetched_at = datetime.datetime.now()
            if ('html' in r.headers['content-type']) and (r.status_code == 200):
                process_expression_content(expression, r.text)
                processed += 1
            else:
                errors += 1
        except Exception as e:
            expression.http_status = '000'
            expression.fetched_at = datetime.datetime.now()
            errors += 1
            print(e)
        expression.save()
    return processed, errors


def add_expression(land: Land, url: str, depth=0) -> Expression:
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
        domain = Domain.get_or_create(name=domain_name)[0]
        expression = Expression.get_or_none(Expression.url == url)
        if expression is None:
            expression = Expression.create(land=land, domain=domain, url=url, depth=depth)
        else:
            print("URL %s already exists in land" % url)
        return expression


def get_domain_name(url: str) -> str:
    """
    Returns domain from any url as sub.domain.ext or according to heuristics settings
    :param url:
    :return:
    """
    domain_name = re.sub('^https?://', '', url[:url.find("/", 9) + 1]).strip('/')
    for k, v in settings.heuristics.items():
        if domain_name.endswith(k):
            matches = re.findall(v, url)
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


def link_expression(land: Land, source_expression: Expression, url: str) -> bool:
    """
    Link target expression to source expression
    :param land:
    :param source_expression:
    :param url:
    :return:
    """
    with DB.atomic():
        target_expression = add_expression(land, url, source_expression.depth + 1)
        if target_expression:
            try:
                ExpressionLink.create(source_id=source_expression.get_id(), target_id=target_expression.get_id())
                return True
            except IntegrityError:
                print("Link from %s to %s already exists" % (source_expression.get_id(), target_expression.get_id()))
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


def process_expression_content(expression: Expression, html: str) -> Expression:
    """
    Process expression fields from HTML content
    :param expression:
    :param html:
    :return:
    """
    soup = BeautifulSoup(html, 'html.parser')
    words = get_land_dictionary(expression.land)

    expression.lang = soup.html.get('lang', '')
    expression.title = soup.title.string.strip()
    expression.description = get_meta_content(soup, 'description')
    expression.keywords = get_meta_content(soup, 'keywords')

    clean_html(soup)
    with open('data/lands/%s/%s' % (expression.land.get_id(), expression.get_id()), 'w') as html_file:
        html_file.write(html.strip())

    expression.readable = get_readable(soup)
    expression.relevance = expression_relevance(words, expression)

    if expression.relevance > 0:
        expression.approved_at = datetime.datetime.now()
        if expression.depth < 3:
            urls = [a.get('href') for a in soup.find_all('a') if is_crawlable(a.get('href'))]
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def get_readable(content):
    """
    Get readable part of HTML content
    :param content:
    :return:
    """
    text = content.get_text(separator=' ')
    lines = text.split("\n")
    text_lines = [l.strip() for l in lines if (len(l.strip()) > 0)]
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


def get_land_dictionary(land: Land):
    """
    Get land dictionary
    :param land:
    :return:
    """
    select = Word.select().join(LandDictionary, JOIN.LEFT_OUTER).where(LandDictionary.land == land)
    return [w.term for w in select]


def land_relevance(land: Land):
    """
    Start relevance computing according to land dictionary for each expression in land
    :param land:
    :return:
    """
    words = get_land_dictionary(land)
    select = Expression.select().where(Expression.land == land, Expression.readable.is_null(False))
    row_count = select.count()
    if row_count > 0:
        print("Updating relevances for %d expressions, it may take some time." % row_count)
        for e in select:
            e.relevance = expression_relevance(words, e)
            e.save()


def expression_relevance(dictionary, expression: Expression) -> int:
    """
    Compute expression relevance according to land dictionary
    :param dictionary:
    :param expression:
    :return:
    """
    stemmed_dict = [stem_word(w) for w in dictionary]
    occurrences = []
    try:
        content = word_tokenize(expression.readable, language='french')
        occurrences = [word for word in content if stem_word(word) in stemmed_dict]
    except:
        pass
    return len(occurrences)


def export_land(land: Land, export_type: str, minimum_relevance: int):
    """
    Export land data
    :param land:
    :param export_type:
    :param minimum_relevance:
    :return:
    """
    date_tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
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
    domains = list(Domain.select().dicts())
    domains = {x['id']: x for x in domains}
    expressions = Expression.select()
    updated = 0
    for expression in expressions:
        domain = get_domain_name(expression.url)
        if domain != domains[expression.domain_id]['name']:
            domain_to_update = Domain.get_by_id(expression.domain_id)
            domain_to_update.name = domain
            domain_to_update.save()
            updated += 1
    print("%d domain(s) updated" % updated)