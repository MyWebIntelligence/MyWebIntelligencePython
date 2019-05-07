"""
Command Line Interface
"""
import argparse
from .controller import *


def command_run(args: dict):
    args = Namespace(**args)
    dispatch(args)


def command_input():
    parser = argparse.ArgumentParser(description='MyWebIntelligence Command Line Project Manager.')
    parser.add_argument('object', metavar='object', type=str, help='Object to interact with [db, land, request]')
    parser.add_argument('verb', metavar='verb', type=str, help='Verb depending on target object')
    parser.add_argument('--land', type=str, help='Name of the land to work with')
    parser.add_argument('--name', type=str, help='Name of the object')
    parser.add_argument('--desc', type=str, help='Description of the object')
    parser.add_argument('--type', type=str, help='Export type [pagecsv, pagegexf, fullpagecsv, nodecsv, nodegexf]')
    parser.add_argument('--terms', type=str, help='Terms to add to request dictionnary, comma separated')
    parser.add_argument('--urls', type=str, help='URL to add to request, comma separated', nargs='?')
    parser.add_argument('--path', type=str, help='Path to local file containing URLs', nargs='?')
    parser.add_argument('--limit', type=int, help='Set limit of URLs to crawl', nargs='?', const=0)
    parser.add_argument('--minrel', type=int, help='Set minimum relevance threshold for exports', nargs='?', const=0)
    parser.add_argument('--http', type=str, help='Limit crawling to specific http status (re crawling)', nargs='?')
    args = parser.parse_args()
    dispatch(args)


def dispatch(args):
    controllers = {
        'db': {
            'setup': DbController.setup
        },
        'domain': {
            'crawl': DomainController.crawl
        },
        'land': {
            'list':    LandController.list,
            'create':  LandController.create,
            'delete':  LandController.delete,
            'crawl':   LandController.crawl,
            'export':  LandController.export,
            'addterm': LandController.addterm,
            'addurl':  LandController.addurl,
            'props':   LandController.properties
        },
        'heuristic': {
            'update': HeuristicController.update
        }
    }
    controller = controllers.get(args.object)
    if controller:
        return call(controller.get(args.verb), args)
    else:
        raise ValueError("Invalid object {}".format(args.object))


def call(func, args):
    if callable(func):
        return func(args)
    else:
        raise ValueError("Invalid action call {} on object {}".format(args.verb, args.object))
