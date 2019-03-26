from peewee import *
import datetime

db = SqliteDatabase('data/mwi.db')


class BaseModel(Model):
    class Meta:
        database = db


class Land(BaseModel):
    name = CharField(unique=True)
    description = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


class Expression(BaseModel):
    land = ForeignKeyField(Land, backref='expressions')
    url = TextField()
    http_status = CharField(max_length=3, null=True)
    title = CharField(null=True)
    lang = CharField(max_length=10, null=True)
    html = TextField(null=True)
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
    source = ForeignKeyField(Expression, backref='links_to')
    target = ForeignKeyField(Expression, backref='linked_by')


class Word(BaseModel):
    term = CharField(max_length=30)
    lemma = CharField(max_length=30)


class LandDictionary(BaseModel):
    class Meta:
        primary_key = CompositeKey('land', 'word')
    land = ForeignKeyField(Land, backref='words')
    word = ForeignKeyField(Word, backref='lands')


class Media(BaseModel):
    expression = ForeignKeyField(Expression, backref='medias')
    url = TextField()
    type = CharField(max_length=30)
