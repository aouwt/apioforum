# view posts in thread

from flask import (
    Blueprint, render_template, abort, request, g, redirect,
    url_for, flash
)
from markdown import markdown
from markupsafe import escape
from .db import get_db

bp = Blueprint("thread", __name__, url_prefix="/thread")

@bp.route("/<int:thread_id>")
def view_thread(thread_id):
    db = get_db()
    thread = db.execute("SELECT * FROM threads WHERE id = ?;",(thread_id,)).fetchone()
    if thread is None:
        abort(404)
    else:
        posts = db.execute(
            "SELECT * FROM posts WHERE thread = ? ORDER BY created ASC;",
            (thread_id,)
        ).fetchall()
        rendered_posts = [markdown(escape(q['content'])) for q in posts]
        return render_template("view_thread.html",posts=posts,thread=thread,thread_id=thread_id,rendered_posts=rendered_posts)

@bp.route("/<int:thread_id>/create_post", methods=("POST",))
def create_post(thread_id):
    if g.user is None:
        flash("you need to log in before you can post")
        return redirect(url_for('thread.view_thread',thread_id=thread_id))
    else:
        db = get_db()
        content = request.form['content']
        thread = db.execute("SELECT * FROM threads WHERE id = ?;",(thread_id,)).fetchone()
        if len(content.strip()) == 0:
            flash("you cannot post an empty message")
        elif not thread:
            flash("that thread does not exist")
        else:
            db.execute(
                "INSERT INTO posts (thread,author,content,created) VALUES (?,?,?,current_timestamp);",
                (thread_id,g.user,content)
            )
            db.execute(
                "UPDATE threads SET updated = current_timestamp WHERE id = ?;",
                (thread_id,)
            )
            db.commit()
            flash("post posted postfully")
    return redirect(url_for('thread.view_thread',thread_id=thread_id))
