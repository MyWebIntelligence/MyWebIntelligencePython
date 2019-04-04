"""
Core functions
"""
from argparse import Namespace
import re
import csv
from lxml import etree
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
    with DB.atomic():
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
            and (parsed.path not in (None, '', '/')) \
            and url.startswith(('http://', 'https://')) \
            and (not url.endswith(exclude_ext))
    except:
        return False


def process_expression_content(expression: Expression, html: str):
    soup = BeautifulSoup(html, 'html.parser')
    words = get_land_dictionary(expression.land)

    expression.title = soup.title.string.strip()

    content = clean_html(soup.body)
    expression.lang = soup.html.get('lang', '')
    expression.html = html
    expression.readable = get_readable(content)
    # expression.published_at
    expression.relevance = expression_relevance(words, expression)
    if expression.relevance > 0:
        expression.approved_at = datetime.datetime.now()

        if expression.depth < 3:
            urls = [a.get('href') for a in content.find_all('a') if is_crawlable(a.get('href'))]
            for url in urls:
                link_expression(expression.land, expression, url)

    return expression


def get_readable(content):
    text = content.get_text(separator=' ')
    lines = text.split("\n")
    text_lines = [l.strip() for l in lines if (len(l.strip()) > 0)]
    return "\n".join(text_lines)


def clean_html(body):
    remove_selectors = ('script', 'style', 'iframe', 'object', 'header', '#header', '.header',
                        'footer', '#footer', '.footer', '.menu', 'nav', '.nav')
    for selector in remove_selectors:
        for tag in body.select(selector):
            tag.decompose()
    return body


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
    e_select = Expression.select().where((Expression.land == land) and (Expression.readable.is_null(False)))
    e_count = e_select.count()
    if e_count > 0:
        print("Updating relevances for %d expressions, it may take some time." % e_count)
        for e in e_select:
            e.relevance = expression_relevance(words, e)
            e.save()


def expression_relevance(dictionary, expression: Expression) -> int:
    stemmed_dict = [stem_word(w) for w in dictionary]
    occurences = []
    try:
        content = word_tokenize(expression.readable, language='french')
        occurences = [word for word in content if stem_word(word) in stemmed_dict]
    except:
        pass
    return len(occurences)


def export_land(land: Land, export_type: str):
    select, fields, extension, call_export = None, None, None, None

    if export_type.startswith('page'):
        fields = [Expression.id, Expression.url, Expression.http_status, Expression.title, Expression.lang,
                  Expression.created_at, Expression.fetched_at, Expression.approved_at, Expression.relevance,
                  Expression.depth]
    elif export_type.startswith('fullpage'):
        fields = [Expression.id, Expression.url, Expression.http_status, Expression.title, Expression.lang,
                  Expression.readable, Expression.created_at, Expression.fetched_at, Expression.approved_at,
                  Expression.relevance, Expression.depth]
    # elif type.startswith('node'):
    # @todo node export

    select = Expression.select(*fields) \
        .where(Expression.land == land) \
        .where(Expression.approved_at.is_null(False))

    if export_type.endswith('csv'):
        extension = 'csv'
        call_export = write_csv
    elif export_type.endswith('gexf'):
        extension = 'gexf'
        call_export = write_gexf

    if select is not None:
        date_tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = 'data/export_%s_%s_%s.%s' % (land.name, export_type, date_tag, extension)
        call_export(filename, select)
        print("Successfully exported %s records to %s" % (select.count(), filename))


def write_csv(filename, select):
    with open(filename, 'w', newline='\n') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        headers = None
        for row in select:
            if headers is None:
                headers = tuple(row.__dict__['__data__'].keys())
                writer.writerow(headers)
            writer.writerow([str(getattr(row, f)) for f in headers])
    file.close()


def write_gexf(filename, select):
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    gexf = etree.Element('gexf', attrib={
        'xmlns': 'http://www.gexf.net/1.2draft',
        'version': '1.2'})
    etree.SubElement(gexf, 'meta', attrib={
        'lastmodifieddate': date,
        'creator': 'MyWebIntelligence'})
    graph = etree.SubElement(gexf, 'graph', attrib={
        'mode': 'static',
        'defaultedgetype': 'directed'})
    nodes = etree.SubElement(graph, 'nodes')
    edges = etree.SubElement(graph, 'edges')
    for row in select:
        etree.SubElement(nodes, 'node', attrib={
            'id': str(row.id),
            'label': row.url})
        for link in row.links_to:
            etree.SubElement(edges, 'edge', attrib={
                'id': "%s_%s" % (row.id, link.target_id),
                'source': str(row.id),
                'target': str(link.target_id)})
    tree = etree.ElementTree(gexf)
    tree.write(filename, xml_declaration=True, pretty_print=True, encoding='utf-8')
