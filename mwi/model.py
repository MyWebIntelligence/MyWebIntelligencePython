"""
Core Model definition
"""

import datetime
from peewee import SqliteDatabase, Model, CharField, TextField, \
    DateTimeField, ForeignKeyField, IntegerField, CompositeKey

DB = SqliteDatabase('data/mwi.db')


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
    created_at = DateTimeField(default=datetime.datetime.now)


class Domain(BaseModel):
    """
    Domain model
    """
    name = CharField()
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
    url = TextField()
    domain = ForeignKeyField(Domain, backref='expressions')
    http_status = CharField(max_length=3, null=True)
    lang = CharField(max_length=10, null=True)
    title = CharField(null=True)
    description = TextField(null=True)
    keywords = TextField(null=True)
    readable = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    published_at = DateTimeField(null=True)
    fetched_at = DateTimeField(null=True)
    approved_at = DateTimeField(null=True)
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


class Project(BaseModel):
    """
    Project model
    """
    land = ForeignKeyField(Land, backref='projects', on_delete='CASCADE')
    name = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


class ProjectExpression(BaseModel):
    """
    Project expression model
    """
    project = ForeignKeyField(Project, backref='expressions', on_delete='CASCADE')
    readable = TextField()


class ProjectTag(BaseModel):
    """
    Project tag model
    color: hex value string as #FF0022
    """
    project = ForeignKeyField(Project, backref='tags', on_delete='CASCADE')
    parent = ForeignKeyField('self', null=True, backref='children', on_delete='CASCADE')
    name = TextField()
    color = CharField(max_length=7)


class TaggedContent(BaseModel):
    tag = ForeignKeyField(ProjectTag, backref='contents', on_delete='CASCADE')
    expression = ForeignKeyField(ProjectExpression, backref='tagged_contents', on_delete='CASCADE')
    text = TextField()
    from_char = IntegerField()
    to_char = IntegerField()