import sqlite3
import click
from flask import current_app, g, abort
from flask.cli import with_appcontext
from werkzeug.routing import BaseConverter

from db_migrations import migrations

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    version = db.execute("PRAGMA user_version;").fetchone()[0]
    for i in range(version, len(migrations)):
        db.executescript(migrations[i])
        db.execute(f"PRAGMA user_version = {i+1}")
        db.commit()
        click.echo(f"migration {i}")

@click.command("migrate")
@with_appcontext
def migrate_command():
    """update database scheme etc"""
    init_db()
    click.echo("ok")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(migrate_command)


class DbWrapper:
    table = None
    primary_key = "id"
    
    # column name -> DbWrapper child class
    # this allows the DbWrapper to automatically fetch the referenced object
    references = {}

    @classmethod
    def get_row(cls, key):
        return get_db().execute(
            f"SELECT * FROM {cls.table} WHERE {cls.primary_key} = ?", (key,))\
                .fetchone()

    @classmethod
    def fetch(cls, key):
        row = cls.get_row(key)
        if row == None: raise KeyError(key)
        return cls(row)

    @classmethod
    def query_some(cls, *args, **kwargs):
        rows = get_db().execute(*args, **kwargs).fetchall()
        for row in rows:
            yield cls(row)

    @classmethod
    def query(cls, *args, **kwargs):
        return(next(cls.query_some(*args, **kwargs)))

    def __init__(self, row):
        self._row = row
        if self.__class__.primary_key:
            self._key = row[self.__class__.primary_key]
        else:
            self._key = None

    def __getattr__(self, attr):
        # special attributes are retrieved from the object itself
        if attr[0] == '_':
            if not attr in self.__dict__:
                raise AttributeError()
            return self.__dict__[attr]

        # changes have been made to the row. fetch it again
        if self._row == None and self._key != None:
            self._row = self.__class__.get_row(self._key)

        # if this column is a reference, fetch the referenced row as an object
        r = self.__class__.references.get(attr, None)
        if r != None:
            # do not fetch it more than once
            if not attr in self.__dict__:
                self.__dict__[attr] = r.fetch(self._row[attr])
            return self.__dict__[attr]

        try:
            return self._row[attr]
        except KeyError as k:
            raise AttributeError() from k

    def __setattr__(self, attr, value):
        if not self.__class__.primary_key:
            raise(RuntimeError('cannot set attributes on this object'))

        # special attributes are set on the object itself
        if attr[0] == '_':
            self.__dict__[attr] = value
            return

        cls = self.__class__

        if not isinstance(value, DbWrapper):
            v = value
        else:
            v = value._key

        print(f"UPDATE {cls.table} SET {attr} = ? WHERE {cls.primary_key} = ?")

        get_db().execute(
            f"UPDATE {cls.table} SET {attr} = ? WHERE {cls.primary_key} = ?",
                (v, self._key))

        # the fetched row is invalidated.
        # avoid extra queries by querying again only if attributes are accessed
        self._row = None

    def __eq__(self, other):
        if self.__class__.primary_key:
            if isinstance(other, self.__class__):
                # rows with keys are equivalent if their keys are
                return self.__class__.table == other.__class__.table\
                        and self._key == other._key
            else:
                # a row can be compared with its key
                return self._key == other
        else:
            return self._row == other._row

    def __conform__(self, protocol):
        # if used in a database query, convert to database key
        if protocol is sqlite3.PrepareProtocol:
            return self._key

# flask path converter
class DbConverter(BaseConverter):
    def __init__(self, m, db_class, abort=True):
        super(DbConverter, self).__init__(m)
        self.db_class = db_class
        self.abort = abort
    
    def to_python(self, value):
        try:
            return self.db_class.fetch(value)
        except KeyError:
            if self.abort:
                abort(404)
            else:
                return None

    def to_url(self, value):
        if isinstance(value, self.db_class):
            return str(value._key)
        else:
            return str(value)

