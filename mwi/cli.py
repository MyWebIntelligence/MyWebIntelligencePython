"""
Command Line Interface
"""
import argparse
from .controller import *


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
    args = parser.parse_args()
    dispatch(args)


def dispatch(args):
    controllers = {
        'db': {
            'setup': DbController.setup
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
    }
    controller = controllers.get(args.object)
    if controller:
        try:
            call(controller.get(args.verb), args)
        except ValueError as e:
            print(e)
        except IntegrityError as e:
            print(e)
    else:
        raise ValueError("Invalid object {}".format(args.object))


def call(func, args):
    if callable(func):
        func(args)
    else:
        raise ValueError("Invalid action call {} on object {}".format(args.verb, args.object))
