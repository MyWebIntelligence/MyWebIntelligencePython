"""
Core Model definition
"""

from os import path
import settings
import datetime
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    TextField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    CompositeKey
)

DB = SqliteDatabase(path.join(settings.data_location, 'mwi.db'), pragmas={
    'journal_mode': 'wal',
    'cache_size': -1 * 512000,
    'foreign_keys': 1,
    'ignore_check_constrains': 0,
    'synchronous': 0
})


class BaseModel(Model):
    """
    BaseModel
    """

    class Meta:
        """
        Meta class to set DB
        """
        database = DB


class Land(BaseModel):
    """
    Land model
    """
    name = CharField(unique=True)
    description = TextField()
    lang = CharField(max_length=10, default='fr')
    created_at = DateTimeField(default=datetime.datetime.now)


class Domain(BaseModel):
    """
    Domain model
    """
    name = CharField(unique=True)
    http_status = CharField(max_length=3, null=True)
    title = TextField(null=True)
    description = TextField(null=True)
    keywords = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    fetched_at = DateTimeField(null=True)


class Expression(BaseModel):
    """
    Expression model
    """
    land = ForeignKeyField(Land, backref='expressions', on_delete='CASCADE')
    url = TextField(index=True)
    domain = ForeignKeyField(Domain, backref='expressions')
    http_status = CharField(max_length=3, null=True, index=True)
    lang = CharField(max_length=10, null=True)
    title = CharField(null=True)
    description = TextField(null=True)
    keywords = TextField(null=True)
    readable = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    published_at = DateTimeField(null=True)
    fetched_at = DateTimeField(null=True, index=True)
    approved_at = DateTimeField(null=True)
    readable_at = DateTimeField(null=True, index=True)
    relevance = IntegerField(null=True)
    depth = IntegerField(null=True)


class ExpressionLink(BaseModel):
    """
    ExpressionLink model
    """

    class Meta:
        """
        Meta class to set composite primary key
        """
        primary_key = CompositeKey('source', 'target')

    source = ForeignKeyField(Expression, backref='links_to', on_delete='CASCADE')
    target = ForeignKeyField(Expression, backref='linked_by', on_delete='CASCADE')


class Word(BaseModel):
    """
    Word model
    """
    term = CharField(max_length=30)
    lemma = CharField(max_length=30)


class LandDictionary(BaseModel):
    """
    LandDictionary model
    """

    class Meta:
        """
        Meta class to set composite primary key
        """
        primary_key = CompositeKey('land', 'word')

    land = ForeignKeyField(Land, backref='words', on_delete='CASCADE')
    word = ForeignKeyField(Word, backref='lands', on_delete='CASCADE')


class Media(BaseModel):
    """
    Media model
    """
    expression = ForeignKeyField(Expression, backref='medias', on_delete='CASCADE')
    url = TextField()
    type = CharField(max_length=30)


"""
Client Model Definition
"""


class Tag(BaseModel):
    """
    Project tag model
    color: hex value string as #FF0022
    """
    land = ForeignKeyField(Land, backref='tags', on_delete='CASCADE')
    parent = ForeignKeyField('self', null=True, backref='children', on_delete='CASCADE')
    name = TextField()
    sorting = IntegerField()
    color = CharField(max_length=7)


class TaggedContent(BaseModel):
    tag = ForeignKeyField(Tag, backref='contents', on_delete='CASCADE')
    expression = ForeignKeyField(Expression, backref='tagged_contents', on_delete='CASCADE')
    text = TextField()
    from_char = IntegerField()
    to_char = IntegerField()
