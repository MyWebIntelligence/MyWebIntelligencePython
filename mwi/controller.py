"""
Application controller
"""
from .core import *
from .model import *


class DbController:
    @staticmethod
    def setup(args: Namespace):
        """
        Creates database model, this is a destructive action as tables are dropped before creation
        :param args:
        :return:
        """
        if confirm("Warning, existing data will be lost, type 'Y' to proceed : "):
            tables = [Land, Expression, ExpressionLink, Word, LandDictionary, Media]
            db.drop_tables(tables)
            db.create_tables(tables)
            print("Model created, setup complete")
        else:
            print("Database setup aborted")


class LandController:
    @staticmethod
    def list(args: Namespace):
        """
        Lists some information about existing lands
        :param args:
        :return:
        """
        lands = Land.select().join(LandDictionary, JOIN.LEFT_OUTER).join(Word, JOIN.LEFT_OUTER)\
            .switch(Land).join(Expression, JOIN.LEFT_OUTER).group_by(Land.name).order_by(Land.name).limit(100)
        if lands.count() > 0:
            for land in lands:
                exp_stats = Expression.select(fn.COUNT(Expression.id).alias('num'))\
                    .join(Land)\
                    .where((Expression.land == land) & (Expression.fetched_at.is_null()))
                to_crawl = [s.num for s in exp_stats]
                print("%s - (%s)\n\t%s" % (land.name, land.created_at.strftime("%B %d %Y %H:%M"), land.description))
                print("\t%s terms in land dictionary %s" % (land.words.count(), [d.word.term for d in land.words]))
                print("\t%s expressions in land (%s remaining to crawl)" % (land.expressions.count(), to_crawl[0]))
        else:
            print("No land created")

    @staticmethod
    def create(args: Namespace):
        """
        Creates land
        :param args:
        :return:
        """
        check_args(args, ('name', 'desc'))
        Land.create(name=args.name, description=args.desc)
        print('Land "%s" created' % args.name)

    @staticmethod
    def addterm(args: Namespace):
        check_args(args, ('land', 'terms'))
        land = Land.get_or_none(Land.name == args.land)
        if land is None:
            print('Land "%s" not found' % args.land)
        else:
            for term in split_arg(args.terms):
                with db.atomic():
                    word, _ = Word.get_or_create(term=term, lemma=stem_word(term))
                    LandDictionary.create(land=land.get_id(), word=word.get_id())
                    print('Term "%s" created in land %s' % (term, args.land))

    @staticmethod
    def addurl(args: Namespace):
        check_args(args, 'land')
        land = Land.get_or_none(Land.name == args.land)
        if land is None:
            print('Land "%s" not found' % args.land)
        else:
            urls_count = 0
            urls = []
            if args.urls:
                urls += [url for url in split_arg(args.urls)]
            if args.path:
                with open(args.path, 'r', encoding='utf-8') as file:
                    urls += file.read().splitlines()
            for url in urls:
                if add_expression(land, url):
                    urls_count += 1
            print('%s URLs created in land %s' % (urls_count, args.land))

    @staticmethod
    def delete(args: Namespace):
        check_args(args, 'name')
        if confirm("Land and underlying objects will be deleted, type 'Y' to proceed : "):
            land = Land.get(Land.name == args.name)
            land.delete_instance(recursive=True)
            print("Land %s deleted" % args.name)

    @staticmethod
    def crawl(args: Namespace):
        check_args(args, 'name')
        land = Land.get_or_none(Land.name == args.name)
        if land is None:
            print('Land "%s" not found' % args.name)
        else:
            print("%d expressions processed" % crawl_land(land))

    @staticmethod
    def export(args: Namespace):
        check_args(args, 'name')
        print("Land export")

    @staticmethod
    def properties(args: Namespace):
        check_args(args, 'name')
        print("Land properties")
