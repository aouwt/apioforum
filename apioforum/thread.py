# view posts in thread

from flask import (
    Blueprint, render_template, abort
)
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
        return render_template("view_thread.html",posts=posts,thread=thread)

