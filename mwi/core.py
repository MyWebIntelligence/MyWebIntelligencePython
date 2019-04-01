"""
Core functions
"""
from argparse import Namespace
import re
from urllib.parse import urlparse
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import FrenchStemmer
import requests
from bs4 import BeautifulSoup
from .model import *


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


def stem_word(word: str) -> str:
    """
    Stems word with NLTK Snowball FrenchStemmer
    :param word:
    :return:
    """
    if 'stemmer' not in stem_word.__dict__:
        stem_word.stemmer = FrenchStemmer()
    return stem_word.stemmer.stem(word.lower())


def crawl_land(land: Land, limit: int = 0) -> int:
    expressions = Expression.select()\
        .where((Expression.land == land) & Expression.fetched_at.is_null())\
        .order_by(Expression.depth)
    if limit > 0:
        expressions = expressions.limit(limit)
    processed = 0
    for expression in expressions:
        try:
            r = requests.get(expression.url)
            expression.http_status = r.status_code
            expression.fetched_at = datetime.datetime.now()
            if ('html' in r.headers['content-type']) & (r.status_code == 200):
                process_expression_content(expression, r.text)
                processed += 1
        except Exception as e:
            print(e)
            expression.http_status = '000'
            expression.fetched_at = datetime.datetime.now()
        # @TODO
        expression.save()
    return processed


def add_expression(land: Land, url: str, depth=0) -> Expression:
    if is_crawlable(url):
        expression = Expression.get_or_none(Expression.url == url)
        if expression is None:
            expression = Expression.create(land=land, url=url, depth=depth)
            return expression
        else:
            print("URL %s already exists in land" % url)


def link_expression(land: Land, source_expression: Expression, url: str) -> bool:
    with db.atomic():
        target_expression = add_expression(land, url, source_expression.depth + 1)
        if target_expression:
            ExpressionLink.create(source_id=source_expression.get_id(), target_id=target_expression.get_id())
            return True
    return False


def is_crawlable(url: str):
    try:
        parsed = urlparse(url)
        exclude_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.pdf',
                       '.txt', '.csv', '.xls', '.xlsx', '.doc', '.docx')

        return \
            (url is not None) \
            & (parsed.path not in (None, '', '/')) \
            & url.startswith(('http://', 'https://')) \
            & (not url.endswith(exclude_ext))
    except:
        return False


def process_expression_content(expression: Expression, html: str):
    soup = BeautifulSoup(html, 'html.parser')
    words = get_land_dictionary(expression.land)

    expression.title = soup.title.string

    content = soup.body
    remove_selectors = ('script', 'style', 'iframe', 'object', 'header', '#header', '.header',
                        'footer', '#footer', '.footer', '.menu', 'nav', '.nav')
    for selector in remove_selectors:
        for tag in content.select(selector):
            tag.decompose()

    # expression.lang
    expression.html = html
    expression.readable = content.get_text(separator=' ').strip()
    # expression.published_at
    relevance = expression_relevance(words, expression)
    expression.relevance = relevance
    if relevance > 0:
        expression.approved_at = datetime.datetime.now()

        if expression.depth < 3:
            urls = [a.get('href') for a in content.find_all('a') if is_crawlable(a.get('href'))]
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def get_land_dictionary(land: Land):
    w_select = Word.select().join(LandDictionary, JOIN.LEFT_OUTER).where(LandDictionary.land == land)
    return [w.term for w in w_select]


def land_relevance(land: Land):
    """
    Compute relevance against land dictionary for each expression in land
    :param land:
    :return:
    """
    words = get_land_dictionary(land)
    e_select = Expression.select().where(Expression.land == land)
    for e in e_select:
        e.relevance = expression_relevance(words, e)
        e.save()


def expression_relevance(words, expression: Expression) -> int:
    counter = 0
    content = word_tokenize(expression.readable)
    for word in content:
        if word in words:
            counter += 1
    return counter
