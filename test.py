from mwi.core import *
from mwi.model import *
from mwi.export import Export
from os import walk

# land = Land.get_or_none(2)
# expression = Expression.get_or_none(3)
# print(process_expression_content(expression, expression.html))

# with open('data/asthme.rtf') as file:
#     urls = file.read().splitlines()
#     count = 0
#     for url in urls:
#         if is_crawlable(url):
#             count += 1
#         print(url)
#     print("%s / %s" % (count, len(urls)))

# land = Land.get(Land.name == 'gj')
# for exp in land.expressions:
#     e = process_expression_content(exp, exp.html)#

#exp = Expression.get_by_id(3718)
#exp = process_expression_content(exp, exp.html)
#print(exp)

#e_select = Expression.select().where((Expression.land == '2') and (Expression.readable.is_null(False)))
#print(e_select.count())

#print(get_domain("https://www.nouvelobs.com/presidentielle-2017/20170507.OBS9079/election-presidentielle-2017-votes-blancs-nuls-et-abstention-records-au-second-tour.html"))

#print(remove_anchor("http://www.example.com/path/to/doc.html"))






#for (dirpath, dirnames, filenames) in walk('data/lands/1'):
#    for f in filenames:
#        with open('data/lands/1/' + f, 'r') as file:
#            html = file.read()
#            soup = BeautifulSoup(html, 'html.parser')
#            clean_html(soup)
#            medias = extract_medias(soup, "https://daten.fr/coucou/une-url/quelconque")
#            print(medias)

#print(e.save())


#with open('data/lands/1/1', 'r') as file:
#    html = file.read()
#    soup = BeautifulSoup(html, 'html.parser')
#    clean_html(soup)
#    extract_media(soup)

#with open('data/asthme.rtf', 'r') as file:
#    urls = file.readlines()
#    for url in urls:
#        if is_crawlable(url):
#            domain = get_domain_name(url)
#            for k, v in settings.heuristics.items():
#                if domain.endswith(k) and (v != ""):
#                    matches = re.findall(v, url)
#                    domain = matches[0] if matches else domain
#                    print(domain)

#print(split_arg("coucou , Juan Branco, satellite"))

"""
land = Land.get(Land.name == 'test_asthme')
sql = """
# SELECT
#     {}
# FROM expression AS e
# JOIN domain AS d ON d.id = e.domain_id
# WHERE land_id = ? AND relevance >= ?
"""

col_map = {
    'id': 'e.id',
    'url': 'e.url',
    'title': 'e.title',
    'description': 'e.description',
    'keywords': 'e.keywords',
    'relevance': 'e.relevance',
    'depth': 'e.depth',
    'domain_id': 'e.domain_id',
    'domain_name': 'd.name',
    'domain_title': 'd.title',
    'domain_description': 'd.description',
    'domain_keywords': 'd.keywords'
}

exp = Export('pagegexf', land, 1)
print(exp.get_sql_cursor(sql, col_map))
"""
land = Land.get(Land.name == "test_comp")
expression = Expression.get(Expression.id == 53293)
dictionnary = get_land_dictionary(land)
rel = expression_relevance(dictionnary, expression)
print(rel)
