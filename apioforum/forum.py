# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for, flash, Response
)
from .db import get_db
from .mdrender import render
from .thread import post_jump

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def view_forum():
    db = get_db()
    threads = db.execute(
        """SELECT threads.id, threads.title, threads.creator, threads.created,
        threads.updated, count(posts.id) as num_replies, max(posts.id), posts.author as last_user
        FROM threads
        INNER JOIN posts ON posts.thread = threads.id
        GROUP BY threads.id
        ORDER BY threads.updated DESC;
        """).fetchall()
    return render_template("view_forum.html",threads=threads)

@bp.route("/create_thread",methods=("GET","POST"))
def create_thread():
    db = get_db()
    
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
        flash(err)
        
        
    return render_template("create_thread.html")

@bp.route("/search")
def search():
    db = get_db()
    query = request.args["q"]
    results = db.execute("""
    SELECT posts.id, highlight(posts_fts, 0, '<mark>', '</mark>') AS content, posts.thread, posts.author, posts.created, posts.edited, posts.updated, threads.title AS thread_title
    FROM posts_fts
    JOIN posts ON posts_fts.rowid = posts.id
    JOIN threads ON threads.id = posts.thread
    WHERE posts_fts MATCH ?
    ORDER BY rank
    LIMIT 50
    """, (query,)).fetchall()

    display_thread_id = [ True ] * len(results)
    last_thread = None
    for ix, result in enumerate(results):
        if result["thread"] == last_thread:
            display_thread_id[ix] = False
        last_thread = result["thread"]
    rendered_posts = [render(q['content']) for q in results]
    return render_template("search_results.html", results=results, query=query, rendered_posts=rendered_posts, display_thread_id=display_thread_id)

@bp.route("/rss")
def rss_feed():
    db = get_db()
    print(request.host_url)
    items = db.execute("SELECT * FROM posts ORDER BY updated DESC LIMIT 50")
    items = [ { **item, "rendered": render(item["content"]), "link": request.base_url + post_jump(item["thread"], item["id"]), "updated": item["updated"] or item["created"] } for item in items ]
    return Response(render_template("rss.xml", title="New posts feed", description="The latest posts on the Apioforum", link=request.base_url, items=items), mimetype="text/xml")