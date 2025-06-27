"""
Application controller
"""
import asyncio
import os
import sys
from typing import Any

from peewee import JOIN, fn
import aiohttp

import settings
from . import core
from . import model


class DbController:
    """
    Db controller class
    """

    @staticmethod
    def migrate(args: core.Namespace):
        """
        Exécute les migrations de base de données.
        """
        from migrations.migrate import MigrationManager
        manager = MigrationManager()
        manager.run_pending_migrations()
        return 1

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

    @staticmethod
    def medianalyse(args: core.Namespace):
        """
        Analyse séquentielle des médias pour un land en batch
        """
        core.check_args(args, 'name')
        depth = core.get_arg_option('depth', args, set_type=int, default=0)
        minrel = core.get_arg_option('minrel', args, set_type=float, default=0.0)
        from .media_analyzer import MediaAnalyzer
        from datetime import datetime
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print(f'Land "{args.name}" introuvable')
            return 0
        
        query = model.Expression.select().where(model.Expression.land == land)
        if depth > 0:
            query = query.where(model.Expression.depth <= depth)
        if minrel > 0:
            query = query.where(model.Expression.relevance >= minrel)
            
        expressions = list(query)
        print(f'Début de l\'analyse médias pour le land "{land.name}" avec {len(expressions)} expressions')
        
        async def process():
            connector = aiohttp.TCPConnector(limit=1, ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                analyzer = MediaAnalyzer(session, {
                    'user_agent': settings.user_agent,
                    'min_width': settings.media_min_width,
                    'min_height': settings.media_min_height,
                    'max_file_size': settings.media_max_file_size,
                    'download_timeout': settings.media_download_timeout,
                    'max_retries': settings.media_max_retries,
                    'analyze_content': settings.media_analyze_content,
                    'extract_colors': settings.media_extract_colors,
                    'extract_exif': settings.media_extract_exif,
                    'n_dominant_colors': settings.media_n_dominant_colors
                })
                for expr in expressions:
                    if not hasattr(expr, 'medias'):
                        continue
                    for media in expr.medias:
                        print(f'Analyse média #{media.id}: {media.url}')
                        result = await analyzer.analyze_image(str(media.url))
                        for field, value in result.items():
                            if hasattr(media, field) and field != 'error':
                                setattr(media, field, value)
                        media.analyzed_at = datetime.now()
                        if 'error' in result:
                            media.analysis_error = result['error']
                        media.save()
                        print('  =>', 'Erreur:' + str(result.get('error', '')) if 'error' in result else 'OK')

        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(process())
        except KeyboardInterrupt:
            print('Analyse interrompue par l\'utilisateur')
        
        return 1


class LandController:
    """
    Land controller class
    """

    @staticmethod
    def medianalyse(args: core.Namespace):
        """
        Analyse médias pour un land
        """
        core.check_args(args, 'name')
        land = model.Land.get_or_none(model.Land.name == args.name)
        if not land:
            print(f'Land "{args.name}" introuvable')
            return 0
            
        print(f'Début analyse média pour {args.name}')
        from .media_analyzer import MediaAnalyzer
        loop = asyncio.get_event_loop()
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
            
        try:
            result = loop.run_until_complete(core.medianalyse_land(land))
            print(f"Analyse terminée : {result['processed']} médias traités")
            return 1
        except Exception as e:
            print(f"Erreur lors de l'analyse : {str(e)}")
            return 0

    @staticmethod
    def consolidate(args: core.Namespace):
        """
        Consolidate a land: recalculates relevance, links, media, adds missing docs, recreates links, replaces old ones.
        :param args:
        :return:
        """
        core.check_args(args, 'name')
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        depth = core.get_arg_option('depth', args, set_type=int, default=None)
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            if sys.platform == 'win32':
                asyncio.set_event_loop(asyncio.ProactorEventLoop())
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(core.consolidate_land(land, fetch_limit, depth))
            print("%d expressions consolidated (%d errors)" % results)
            return 1
        return 0


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
                if land.words is not None:
                    words = [w for w in land.words.split(',')]
                else:
                    words = []

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
        # Store lang as comma-separated string
        lang_str = ",".join(args.lang) if isinstance(args.lang, list) else str(args.lang)
        land = model.Land.create(name=args.name, description=args.desc, lang=lang_str)
        os.makedirs(os.path.join(settings.data_location, 'lands/%s') % land.id, exist_ok=True)
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
                    lemma = ' '.join([core.stem_word(w) for w in term.split(' ')])
                    word, _ = model.Word.get_or_create(term=term, lemma=lemma)
                    model.LandDictionary.create(land=land.id, word=word.id)
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
                    print(f"Added URL: {url} to land {args.land}")
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
            land = model.Land.get_or_none(model.Land.name == args.name)
            if land is None:
                print('Land "%s" not found' % args.name)
                return 0
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
        depth = core.get_arg_option('depth', args, set_type=int, default=None)
        if depth is not None:
            print('Only crawling URLs with depth = %s' % depth)
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(core.crawl_land(land, fetch_limit, http_status, depth))
            print("%d expressions processed (%d errors)" % results)
            return 1
        return 0

    @staticmethod
    def readable(args: core.Namespace):
        """
        Pipeline Mercury Parser pour l'extraction readable enrichie
        :param args:
        :return:
        """
        core.check_args(args, 'name')
        
        # Récupération des paramètres
        fetch_limit = core.get_arg_option('limit', args, set_type=int, default=0)
        depth_limit = core.get_arg_option('depth', args, set_type=int, default=None)
        merge_strategy = core.get_arg_option('merge', args, set_type=str, default='smart_merge')
        
        if fetch_limit > 0:
            print(f'Fetch limit set to {fetch_limit} URLs')
        if depth_limit is not None:
            print(f'Depth limit set to {depth_limit}')
        print(f'Merge strategy: {merge_strategy}')
        
        land = model.Land.get_or_none(model.Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
            return 0
        
        # Import du nouveau pipeline
        from .readable_pipeline import run_readable_pipeline
        
        # Configuration de l'event loop selon la plateforme
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            run_readable_pipeline(land, fetch_limit, depth_limit, merge_strategy)
        )
        
        print("%d expressions processed (%d errors)" % results)
        return 1

    @staticmethod
    def export(args: core.Namespace):
        """
        Export land
        :param args:
        :return:
        """
        minimum_relevance = 1
        core.check_args(args, ('name', 'type'))
        valid_types = ['pagecsv', 'fullpagecsv', 'nodecsv', 'pagegexf',
                       'nodegexf', 'mediacsv', 'corpus']

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
