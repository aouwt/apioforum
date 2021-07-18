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
    g.db.execute("PRAGMA foreign_keys = ON;")
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
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    creator TEXT NOT NULL REFERENCES users(username),
    created TIMESTAMP NOT NULL,
    updated TIMESTAMP NOT NULL
);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    content TEXT,
    thread INTEGER NOT NULL REFERENCES threads(id),
    author TEXT NOT NULL REFERENCES users(username),
    created TIMESTAMP NOT NULL
);

CREATE INDEX posts_thread_idx ON posts (thread);
""",
"""
ALTER TABLE posts ADD COLUMN edited INT NOT NULL DEFAULT 0;
ALTER TABLE posts ADD COLUMN updated TIMESTAMP;
""",
"""
CREATE VIRTUAL TABLE posts_fts USING fts5(
    content,
    content=posts,
    content_rowid=id,
    tokenize='porter unicode61 remove_diacritics 2'
);
INSERT INTO posts_fts (rowid, content) SELECT id, content FROM posts;

CREATE TRIGGER posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
CREATE TRIGGER posts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO posts_fts(rowid, content) VALUES (new.id, new.content);
END;
""",
"""
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    text_colour TEXT NOT NULL,
    bg_colour TEXT NOT NULL
);
CREATE TABLE thread_tags (
    thread INTEGER NOT NULL REFERENCES threads(id),
    tag INTEGER NOT NULL REFERENCES tags(id)
);
""",
"""CREATE INDEX thread_tags_thread ON thread_tags (thread);""",
"""ALTER TABLE users ADD COLUMN admin INT NOT NULL DEFAULT 0""",
"""
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN joined TIMESTAMP;
""",
"""
CREATE TABLE polls (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
);
ALTER TABLE threads ADD COLUMN poll INTEGER REFERENCES polls(id);

CREATE TABLE poll_options (
    poll INTEGER NOT NULL REFERENCES polls(id),
    text TEXT NOT NULL,
    option_idx INTEGER NOT NULL,
    PRIMARY KEY ( poll, option_idx )
);

CREATE TABLE votes (
    id INTEGER PRIMARY KEY,
    user TEXT NOT NULL REFERENCES users(username),
    poll INTEGER NOT NULL,
    option_idx INTEGER,
    time TIMESTAMP NOT NULL,
    current INTEGER NOT NULL,
    is_retraction INTEGER,
    CHECK (is_retraction OR (option_idx NOT NULL)),
    FOREIGN KEY ( poll, option_idx ) REFERENCES poll_options(poll, option_idx)
);
ALTER TABLE posts ADD COLUMN vote INTEGER REFERENCES votes(id);
""",
"""
CREATE VIEW vote_counts AS
    SELECT poll, option_idx, count(*) AS num FROM votes WHERE current GROUP BY option_idx,poll; 
""",
"""
CREATE TABLE forums (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    parent INTEGER REFERENCES forums(id),
    description TEXT
);
INSERT INTO forums (name,parent,description) values ('apioforum',null,
        'welcome to the apioforum\n\n' ||
        'forum rules: do not be a bad person. do not do bad things.');

PRAGMA foreign_keys = off;
BEGIN TRANSACTION;
CREATE TABLE threads_new (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    creator TEXT NOT NULL,
    created TIMESTAMP NOT NULL,
    updated TIMESTAMP NOT NULL,
    forum NOT NULL REFERENCES forums(id),
    poll INTEGER REFERENCES polls(id)
);
INSERT INTO threads_new (id,title,creator,created,updated,forum)
    SELECT id,title,creator,created,updated,1 FROM threads;
DROP TABLE threads;
ALTER TABLE threads_new RENAME TO threads;
COMMIT;
PRAGMA foreign_keys = on;
""",
"""
CREATE VIEW most_recent_posts AS
    SELECT max(id), * FROM posts GROUP BY thread;

CREATE VIEW number_of_posts AS
    SELECT thread, count(*) AS num_replies FROM posts GROUP BY thread;
""",
"""
CREATE VIEW total_vote_counts AS
    SELECT poll, count(*) AS total_votes FROM votes WHERE current AND NOT is_retraction GROUP BY poll;
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

