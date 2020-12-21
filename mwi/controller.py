"""
Application controller
"""
import asyncio
import os
import sys

from peewee import JOIN, fn

import settings
from . import core
from . import model


class DbController:
    """
    Db controller class
    """

    @staticmethod
    def setup(args: core.Namespace):
        """
        Creates database model, this is a destructive action as tables are dropped before creation
        :param args:
        :return:
        """
        tables = [model.Land, model.Domain, model.Expression, model.ExpressionLink, model.Word,
                  model.LandDictionary, model.Media, model.Tag, model.TaggedContent]

        if core.confirm("Warning, existing data will be lost, type 'Y' to proceed : "):
            model.DB.drop_tables(tables)
            model.DB.create_tables(tables)
            print("Model created, setup complete")
            return 1
        print("Database setup aborted")
        return 0


class LandController:
    """
    Land controller class
    """

    @staticmethod
    def list(args: core.Namespace):
        """
        Lists some information about existing lands
        :param args:
        :return:
        """
        lands = model.Land.select(
            model.Land.id,
            model.Land.name,
            model.Land.created_at,
            model.Land.description,
            fn.GROUP_CONCAT(model.Word.term.distinct()).alias('words'),
            fn.COUNT(model.Expression.id.distinct()).alias('num_all')
        ) \
            .join(model.LandDictionary, JOIN.LEFT_OUTER) \
            .join(model.Word, JOIN.LEFT_OUTER) \
            .switch(model.Land) \
            .join(model.Expression, JOIN.LEFT_OUTER) \
            .group_by(model.Land.name) \
            .order_by(model.Land.name)

        name = core.get_arg_option('name', args, set_type=str, default=None)
        if name is not None:
            lands = lands.where(model.Land.name == name)

        if lands.count() > 0:
            for land in lands:
                words = [w for w in land.words.split(',')]

                select = model.Expression \
                    .select(fn.COUNT(model.Expression.id).alias('num')) \
                    .join(model.Land) \
                    .where((model.Expression.land == land)
                           & (model.Expression.fetched_at.is_null()))
                remaining_to_crawl = [s.num for s in select]

                select = model.Expression \
                    .select(
                        model.Expression.http_status,
                        fn.COUNT(model.Expression.http_status).alias('num')) \
                    .where((model.Expression.land == land)
                           & (model.Expression.fetched_at.is_null(False))) \
                    .group_by(model.Expression.http_status) \
                    .order_by(model.Expression.http_status)
                http_statuses = ["%s: %s" % (s.http_status, s.num) for s in select]

                print("%s - (%s)\n\t%s" % (
                    land.name,
                    land.created_at.strftime("%B %d %Y %H:%M"),
                    land.description))
                print("\t%s terms in land dictionary %s" % (
                    len(words),
                    words))
                print("\t%s expressions in land (%s remaining to crawl)" % (
                    land.num_all,
                    remaining_to_crawl[0]))
                print("\tStatus codes: %s" % (
                    " - ".join(http_statuses)))
                print("\n")
            return 1
        print("No land created")
        return 0

    @staticmethod
    def create(args: core.Namespace):
        """
        Creates land
        :param args:
        :return:
        """
        core.check_args(args, ('name', 'desc'))
        land = model.Land.create(name=args.name, description=args.desc)
        os.makedirs(os.path.join(settings.data_location, 'lands/%s') % land.get_id(), exist_ok=True)
        print('Land "%s" created' % args.name)
        return 1

    @staticmethod
    def addterm(args: core.Namespace):
        """
        Add terms to land dictionary
        :param args:
        :return:
        """
        core.check_args(args, ('land', 'terms'))
        land = model.Land.get_or_none(model.Land.name == args.land)
        if land is None:
            print('Land "%s" not found' % args.land)
        else:
            for term in core.split_arg(args.terms):
                with model.DB.atomic():
                    word, _ = model.Word.get_or_create(term=term, lemma=core.stem_word(term))
                    model.LandDictionary.create(land=land.get_id(), word=word.get_id())
                    print('Term "%s" created in land %s' % (term, args.land))
            core.land_relevance(land)
            return 1
        return 0

    @staticmethod
    def addurl(args: core.Namespace):
        """
        Add URLs to land
        :param args:
        :return:
        """
        core.check_args(args, 'land')
        land = model.Land.get_or_none(model.Land.name == args.land)
        if land is None:
            print('Land "%s" not found' % args.land)
        else:
            urls_count = 0
            urls = []
            if args.urls:
                urls += [url for url in core.split_arg(args.urls)]
            if args.path:
                with open(args.path, 'r', encoding='utf-8') as file:
                    urls += file.read().splitlines()
            for url in urls:
                if core.add_expression(land, url):
                    urls_count += 1
            print('%s URLs created in land %s' % (urls_count, args.land))
            return 1
        return 0

    @staticmethod
    def delete(args: core.Namespace):
        """
        Delete land
        :param args:
        :return:
        """
        core.check_args(args, 'name')
        maxrel = core.get_arg_option('maxrel', args, set_type=int, default=0)

        if core.confirm("Land and/or underlying objects will be deleted, type 'Y' to proceed : "):
            land = model.Land.get(model.Land.name == args.name)
            if maxrel > 0:
                query = model.Expression.delete().where((model.Expression.land == land)
                                                & (model.Expression.relevance < maxrel)
                                                & (model.Expression.fetched_at.is_null(False)))
                query.execute()
                print("Expressions deleted")
            else:
                land.delete_instance(recursive=True)
                print("Land %s deleted" % args.name)
            return 1
        return 0

    @staticmethod
    def crawl(args: core.Namespace):
        """
        Crawl land
        :param args:
        :return:
        """
        core.check_args(args, 'name')
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        if fetch_limit > 0:
            print('Fetch limit set to %s URLs' % fetch_limit)
        http_status = core.get_arg_option('http', args, set_type=str, default=None)
        if http_status is not None:
            print('Limited to %s HTTP status code' % http_status)
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(core.crawl_land(land, fetch_limit, http_status))
            print("%d expressions processed (%d errors)" % results)
            return 1
        return 0

    @staticmethod
    def readable(args: core.Namespace):
        """
        Fetch readable from Mercury Parser for expressions in land
        :param args:
        :return:
        """
        core.check_args(args, 'name')
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        if fetch_limit > 0:
            print('Fetch limit set to %s URLs' % fetch_limit)
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            if sys.platform == 'win32':
                asyncio.set_event_loop(asyncio.ProactorEventLoop())
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(core.readable_land(land, fetch_limit))
            print("%d expressions processed (%d errors)" % results)
            return 1
        return 0

    @staticmethod
    def export(args: core.Namespace):
        """
        Export land
        :param args:
        :return:
        """
        minimum_relevance = 1
        core.check_args(args, ('name', 'type'))
        valid_types = ['pagecsv', 'fullpagecsv', 'nodecsv', 'pagegexf', 'nodegexf', 'mediacsv']

        if isinstance(args.minrel, int) and (args.minrel >= 0):
            minimum_relevance = args.minrel
            print("Minimum relevance set to %s" % minimum_relevance)
            
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            if args.type in valid_types:
                core.export_land(land, args.type, minimum_relevance)
                return 1
            print('Invalid export type "%s" [%s]' % (args.type, ', '.join(valid_types)))
        return 0


class DomainController:
    """
    Domain controller class
    """

    @staticmethod
    def crawl(args: core.Namespace):
        """
        Crawl domains
        :param args:
        :return:
        """
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        http_status = core.get_arg_option('http', args, set_type=str, default=None)
        print("%d domains processed" % core.crawl_domains(fetch_limit, http_status))
        return 1


class TagController:
    """
    Tag controller class
    """

    @staticmethod
    def export(args: core.Namespace):
        """
        Export tags
        :param args:
        :return:
        """
        minimum_relevance = 1
        core.check_args(args, ('name', 'type'))
        valid_types = ['matrix', 'content']

        if isinstance(args.minrel, int) and (args.minrel >= 0):
            minimum_relevance = args.minrel
            print("Minimum relevance set to %s" % minimum_relevance)

        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            if args.type in valid_types:
                core.export_tags(land, args.type, minimum_relevance)
                return 1
            print('Invalid export type "%s" [%s]' % (args.type, ', '.join(valid_types)))
        return 0


class HeuristicController:
    """
    Heuristic controller class
    """

    @staticmethod
    def update(args: core.Namespace):
        """
        Update domains from specified heuristics
        :param args:
        :return:
        """
        core.update_heuristic()
        return 1
