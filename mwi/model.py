from peewee import *
import datetime

DB = SqliteDatabase('data/mwi.db')


class BaseModel(Model):
    class Meta:
        database = DB


class Land(BaseModel):
    name = CharField(unique=True)
    description = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


class Domain(BaseModel):
    schema = CharField()
    name = CharField()
    title = TextField(null=True)
    description = TextField(null=True)
    keywords = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    fetched_at = DateTimeField(null=True)

    class Meta:
        indexes = (
            (('schema', 'name'), True),
        )


class Expression(BaseModel):
    land = ForeignKeyField(Land, backref='expressions', on_delete='CASCADE')
    url = TextField()
    domain = ForeignKeyField(Domain, backref='expressions')
    http_status = CharField(max_length=3, null=True)
    title = CharField(null=True)
    lang = CharField(max_length=10, null=True)
    readable = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    published_at = DateTimeField(null=True)
    fetched_at = DateTimeField(null=True)
    approved_at = DateTimeField(null=True)
    relevance = IntegerField(null=True)
    depth = IntegerField(null=True)


class ExpressionLink(BaseModel):
    class Meta:
        primary_key = CompositeKey('source', 'target')
    source = ForeignKeyField(Expression, backref='links_to', on_delete='CASCADE')
    target = ForeignKeyField(Expression, backref='linked_by', on_delete='CASCADE')


class Word(BaseModel):
    term = CharField(max_length=30)
    lemma = CharField(max_length=30)


class LandDictionary(BaseModel):
    class Meta:
        primary_key = CompositeKey('land', 'word')
    land = ForeignKeyField(Land, backref='words', on_delete='CASCADE')
    word = ForeignKeyField(Word, backref='lands', on_delete='CASCADE')


class Media(BaseModel):
    expression = ForeignKeyField(Expression, backref='medias', on_delete='CASCADE')
    url = TextField()
    type = CharField(max_length=30)
