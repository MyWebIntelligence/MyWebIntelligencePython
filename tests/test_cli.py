import pytest
from mwi.cli import *
from argparse import Namespace


def test_all_commands():
    commands = [
        {'object': 'land', 'verb': 'create', 'name': 'test_asthme', 'desc': 'Asthme chez les jeunes'},
        {'object': 'land', 'verb': 'addterm', 'land': 'test_asthme', 'terms': 'asthme, asthmatique, jeune, enfant, adolescent, nourrisson, bébé, nouveau-né'},
        {'object': 'land', 'verb': 'addurl', 'land': 'test_asthme', 'path': 'data/asthme-50.txt', 'urls': None},
        {'object': 'land', 'verb': 'list'},
        {'object': 'land', 'verb': 'crawl', 'name': 'test_asthme', 'limit': 2},
        {'object': 'domain', 'verb': 'crawl', 'limit': 2},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'pagecsv', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'pagegexf', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'nodegexf', 'minrel': 1},
    ]
    for command in commands:
        args = Namespace(**command)
        ret = dispatch(args)
        assert ret == 1
