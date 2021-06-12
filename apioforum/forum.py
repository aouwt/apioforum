# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for
)
from .db import get_db

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def view_forum():
    db = get_db()
    threads = db.execute("SELECT * FROM threads ORDER BY updated DESC;").fetchall()
    return render_template("view_forum.html",threads=threads)

@bp.route("/create_thread",methods=("GET","POST"))
def create_thread():
    db = get_db()
    if request.method == "POST":
        title = request.form['title']
        content = request.form['content']
        err = None
        if g.user is None:
            err = "you need to be logged in to create a thread"
        elif len(title.strip()) == 0 or len(content.strip()) == 0:
            err = "title and content can't be empty"

        if err is None:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO threads (title,creator,created,updated) VALUES (?,?,current_timestamp,current_timestamp);",
                (title,g.user)
            )
            thread_id = cur.lastrowid
            cur.execute(
                "INSERT INTO posts (thread,created,author,content) VALUES (?,current_timestamp,?,?);",
                (thread_id,g.user,content)
            )
            db.commit()
            return redirect(url_for('thread.view_thread',thread_id=thread_id))
        
        
    return render_template("create_thread.html")

