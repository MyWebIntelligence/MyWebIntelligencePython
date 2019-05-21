from .model import *
import csv
import datetime
from lxml import etree


class Export:

    gexf_ns = {None: 'http://www.gexf.net/1.2draft', 'viz': 'http://www.gexf.net/1.1draft/viz'}
    types = ['pagecsv', 'fullpagecsv', 'nodecsv', 'pagegexf', 'nodegexf']
    type = None
    land = None
    relevance = 1

    def __init__(self, export_type: str, land: Land, minimum_relevance: int):
        """
        :param export_type:
        :param land:
        :param minimum_relevance:
        :return:
        """
        self.type = export_type
        self.land = land
        self.relevance = minimum_relevance

    def write(self, export_type: str, filename):
        call_write = getattr(self, 'write_' + export_type)
        if export_type.endswith('csv'):
            filename += '.csv'
        elif export_type.endswith('gexf'):
            filename += '.gexf'
        return call_write(filename)

    def write_pagecsv(self, filename) -> int:
        """
        Write CSV file
        :param filename:
        :return:
        """
        sql = """
            SELECT
                e.id,
                e.url,
                e.title,
                e.description,
                e.keywords,
                e.relevance,
                e.depth,
                e.domain_id,
                d.name AS domain_name,
                d.description AS domain_description,
                d.keywords AS domain_keywords
            FROM expression AS e
            JOIN domain AS d ON d.id = e.domain_id
            WHERE land_id = ? AND relevance >= ?
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['id', 'url', 'title', 'description', 'keywords', 'relevance', 'depth', 'domain_id',
                'domain_name', 'domain_description', 'domain_keywords']
        return self.write_csv(filename, keys, cursor)

    def write_fullpagecsv(self, filename) -> int:
        """
        Write CSV file
        :param filename:
        :return:
        """
        sql = """
            SELECT
                e.id,
                e.url,
                e.title,
                e.description,
                e.keywords,
                e.readable,
                e.relevance,
                e.depth,
                e.domain_id,
                d.name AS domain_name,
                d.description AS domain_description,
                d.keywords AS domain_keywords
            FROM expression AS e
            JOIN domain AS d ON d.id = e.domain_id
            WHERE land_id = ? AND relevance >= ?
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['id', 'url', 'title', 'description', 'keywords', 'relevance', 'depth', 'readable',
                'domain_id', 'domain_name', 'domain_description', 'domain_keywords']
        return self.write_csv(filename, keys, cursor)

    def write_nodecsv(self, filename) -> int:
        """
        Write CSV file
        :param filename:
        :return:
        """
        sql = """
            SELECT
                d.id,
                d.name,
                d.description,
                d.keywords,
                COUNT(*) AS expressions,
                ROUND(AVG(e.relevance), 2) AS average_relevance
            FROM domain AS d
            JOIN expression AS e ON e.domain_id = d.id
            WHERE land_id = ? AND e.relevance >= ?
            GROUP BY d.id
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['id', 'name', 'description', 'keywords', 'expressions', 'average_relevance']
        return self.write_csv(filename, keys, cursor)

    @staticmethod
    def write_csv(filename, keys, cursor):
        count = 0
        with open(filename, 'w', newline='\n', encoding="utf-8") as file:
            writer = csv.writer(file, quoting=csv.QUOTE_ALL)
            header = False
            for row in cursor:
                if not header:
                    writer.writerow(keys)
                    header = True
                writer.writerow(row)
                count += 1
        file.close()
        return count

    def write_pagegexf(self, filename) -> int:
        count = 0
        attributes = [('description', 'string'), ('keywords', 'string'), ('domain_id', 'string'),
                      ('relevance', 'integer'), ('depth', 'integer')]
        gexf, nodes, edges = self.get_gexf(attributes)

        sql = """
            SELECT
                e.id,
                e.url,
                e.title,
                e.description,
                e.keywords,
                e.relevance,
                e.depth,
                e.domain_id,
                d.name AS domain_name,
                d.description AS domain_description,
                d.keywords AS domain_keywords
            FROM expression AS e
            JOIN domain AS d ON d.id = e.domain_id
            WHERE land_id = ? AND relevance >= ?
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['id', 'url', 'title', 'description', 'keywords', 'relevance', 'depth', 'domain_id',
                'domain_name', 'domain_description', 'domain_keywords']

        for row in cursor:
            self.gexf_node(dict(zip(keys, row)), nodes, attributes, 'url', 'relevance')
            count += 1

        sql = """
            WITH idx(x) AS (
                SELECT
                    id
                FROM expression
                WHERE land_id = ? AND relevance >= ?
            )
            SELECT
                link.source_id,
                e1.domain_id AS source_domain_id,
                link.target_id,
                e2.domain_id AS target_domain_id
            FROM expressionlink AS link
            JOIN expression AS e1 ON e1.id = link.source_id
            JOIN expression AS e2 ON e2.id = link.target_id
            WHERE source_id IN idx AND target_id IN idx
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['source_id', 'source_domain_id', 'target_id', 'target_domain_id', 'weight']

        for row in cursor:
            row = dict(zip(keys, row))
            self.gexf_edge([row['source_id'], row['target_id'], 1], edges)

        tree = etree.ElementTree(gexf)
        tree.write(filename, xml_declaration=True, pretty_print=True, encoding='utf-8')
        return count

    def write_nodegexf(self, filename) -> int:
        count = 0
        attributes = [('description', 'string'), ('keywords', 'string'),
                      ('expressions', 'integer'), ('average_relevance', 'float')]
        gexf, nodes, edges = self.get_gexf(attributes)

        sql = """
            SELECT
                d.id,
                d.name,
                d.description,
                d.keywords,
                COUNT(*) AS expressions,
                ROUND(AVG(e.relevance), 2) AS average_relevance
            FROM domain AS d
            JOIN expression AS e ON e.domain_id = d.id
            WHERE land_id = ? AND relevance >= ?
            GROUP BY d.name
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['id', 'name', 'description', 'keywords', 'expressions', 'average_relevance']

        for row in cursor:
            self.gexf_node(dict(zip(keys, row)), nodes, attributes, 'name', 'average_relevance')
            count += 1

        sql = """
            WITH idx(x) AS (
                SELECT
                    id
                FROM expression
                WHERE land_id = ? AND relevance >= ?
            )
            SELECT
                link.source_id,
                e1.domain_id AS source_domain_id,
                link.target_id,
                e2.domain_id AS target_domain_id,
                COUNT(*) AS weight
            FROM expressionlink AS link
            JOIN expression AS e1 ON e1.id = link.source_id
            JOIN expression AS e2 ON e2.id = link.target_id
            WHERE source_id IN idx AND target_id IN idx
            GROUP BY source_domain_id, target_domain_id
        """
        cursor = DB.execute_sql(sql, (self.land.get_id(), self.relevance))
        keys = ['source_id', 'source_domain_id', 'target_id', 'target_domain_id', 'weight']

        for row in cursor:
            row = dict(zip(keys, row))
            self.gexf_edge([row['source_domain_id'], row['target_domain_id'], row['weight']], edges)

        tree = etree.ElementTree(gexf)
        tree.write(filename, xml_declaration=True, pretty_print=True, encoding='utf-8')
        return count

    def get_gexf(self, attributes: list) -> tuple:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        gexf = etree.Element('gexf', nsmap=self.gexf_ns, attrib={'version': '1.2'})
        etree.SubElement(gexf, 'meta', attrib={'lastmodifieddate': date, 'creator': 'MyWebIntelligence'})
        graph = etree.SubElement(gexf, 'graph', attrib={'mode': 'static', 'defaultedgetype': 'directed'})
        attr = etree.SubElement(graph, 'attributes', attrib={'class': 'node'})
        for i, attribute in enumerate(attributes):
            etree.SubElement(attr, 'attribute', attrib={'id': str(i), 'title': attribute[0], 'type': attribute[1]})
        nodes = etree.SubElement(graph, 'nodes')
        edges = etree.SubElement(graph, 'edges')
        return gexf, nodes, edges

    def gexf_node(self, row: dict, nodes, attributes: list, label_key: str, size_key: str):
        node = etree.SubElement(nodes, 'node', attrib={
            'id': str(row['id']),
            'label': row[label_key]})
        etree.SubElement(node, '{%s}size' % self.gexf_ns['viz'], attrib={'value': str(row[size_key])})
        attvalues = etree.SubElement(node, 'attvalues')
        for i, attribute in enumerate(attributes):
            etree.SubElement(attvalues, 'attvalue', attrib={'for': str(i), 'value': str(row[attribute[0]])})

    def gexf_edge(self, values, edges):
        etree.SubElement(edges, 'edge', attrib={
            'id': "%s_%s" % (values[0], values[1]),
            'source': str(values[0]),
            'target': str(values[1]),
            'weight': str(values[2])})
