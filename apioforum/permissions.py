from flask import (
    g, redirect, url_for, flash
)
import functools
import click
from flask.cli import with_appcontext
from .db import get_db

def is_admin():
    if g.user_info is None:
        return False
    else:
        return g.user_info['admin'] > 0

def admin_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if is_admin():
            return view(**kwargs)
        else:
            flash("you must be an admin to do that")
            return redirect(url_for("index"))
    return wrapped

@click.command("make_admin")
@click.argument("username")
@with_appcontext
def make_admin(username):
    """makes a user an admin user"""
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE users SET admin = 1 WHERE username = ?",(username,))
    if cur.rowcount == 0:
        click.echo("no such user found")
    else:
        click.echo("ok")
    db.commit()

def init_app(app):
    app.cli.add_command(make_admin)

