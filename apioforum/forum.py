# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for, flash
)

from .db import get_db
from .mdrender import render

from sqlite3 import OperationalError

from sqlite3 import OperationalError

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def not_actual_index():
    return redirect("/1")

@bp.route("/<int:forum_id>")
def view_forum(forum_id):
    db = get_db()
    forum = db.execute("SELECT * FROM forums WHERE id = ?",(forum_id,)).fetchone()
    threads = db.execute(
        """SELECT threads.id, threads.title, threads.creator, threads.created,
        threads.updated, count(posts.id) as num_replies, max(posts.id), posts.author as last_user
        FROM threads
        INNER JOIN posts ON posts.thread = threads.id
        WHERE threads.forum = ?
        GROUP BY threads.id
        ORDER BY threads.updated DESC;
        """,(forum_id,)).fetchall()
    thread_tags = {}
    preview_post = {}
    #todo: somehow optimise this
    for thread in threads:
        thread_tags[thread['id']] = db.execute(
            """SELECT tags.* FROM tags
            INNER JOIN thread_tags ON thread_tags.tag = tags.id
            WHERE thread_tags.thread = ?
            ORDER BY tags.id;
            """,(thread['id'],)).fetchall()
        preview_post[thread['id']]  = db.execute(
            """SELECT * FROM posts WHERE thread = ?
            ORDER BY created DESC;
            """,(thread['id'],)).fetchone()
    return render_template("view_forum.html",
            forum=forum,
            threads=threads,
            thread_tags=thread_tags,
            preview_post=preview_post
            )

@bp.route("/<int:forum_id>/create_thread",methods=("GET","POST"))
def create_thread(forum_id):
    db = get_db()
    forum = db.execute("SELECT * FROM forums WHERE id = ?",(forum_id,)).fetchone()
    if forum is None:
        flash("that forum doesn't exist")
        return redirect(url_for('index'))
    
    if g.user is None:
        flash("you need to be logged in to create a thread")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        title = request.form['title']
        content = request.form['content']
        err = None
        if len(title.strip()) == 0 or len(content.strip()) == 0:
            err = "title and content can't be empty"

        if err is None:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO threads (title,creator,created,updated,forum) VALUES (?,?,current_timestamp,current_timestamp,?);",
                (title,g.user,forum_id)
            )
            thread_id = cur.lastrowid
            cur.execute(
                "INSERT INTO posts (thread,created,author,content) VALUES (?,current_timestamp,?,?);",
                (thread_id,g.user,content)
            )
            db.commit()
            return redirect(url_for('thread.view_thread',thread_id=thread_id))
        flash(err)
        
        
    return render_template("create_thread.html")

@bp.route("/search")
def search():
    db = get_db()
    query = request.args["q"]
    try:
        results = db.execute("""
        SELECT posts.id, highlight(posts_fts, 0, '<mark>', '</mark>') AS 
            content, posts.thread, posts.author, posts.created, posts.edited, 
            posts.updated, threads.title AS thread_title
        FROM posts_fts
        JOIN posts ON posts_fts.rowid = posts.id
        JOIN threads ON threads.id = posts.thread
        WHERE posts_fts MATCH ?
        ORDER BY rank
        LIMIT 50
        """, (query,)).fetchall()
    except OperationalError:
        flash('your search query was malformed.')
        return redirect(url_for("forum.view_forum"))

    display_thread_id = [ True ] * len(results)
    last_thread = None
    for ix, result in enumerate(results):
        if result["thread"] == last_thread:
            display_thread_id[ix] = False
        last_thread = result["thread"]
    return render_template("search_results.html", results=results, query=query, display_thread_id=display_thread_id)
