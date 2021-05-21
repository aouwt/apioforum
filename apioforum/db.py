import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    g.db.execute("PRAGMA foreighn_keys = ON;")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

migrations = [
"""
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
);""",
"""
CREATE TABLE threads (
    id INT PRIMARY KEY,
    title TEXT NOT NULL,
    creator TEXT NOT NULL REFERENCES users(username),
    created INT NOT NULL,
    updated INT NOT NULL
);
CREATE TABLE posts (
    id INT PRIMARY KEY,
    content TEXT,
    thread INT NOT NULL REFERENCES threads(id),
    author TEXT NOT NULL REFERENCES users(username),
    idx INT NOT NULL
);
CREATE INDEX posts_thread_idx ON posts (thread);
""",
]

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

