# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for, flash
)

from .db import get_db
from .mdrender import render

from sqlite3 import OperationalError
import datetime

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def not_actual_index():
    return redirect("/1")

def get_avail_tags(forum_id):
    db = get_db()
    tags = db.execute("""
    	WITH RECURSIVE fs AS
    		(SELECT * FROM forums WHERE id = ?
    		 UNION ALL
    		 SELECT forums.* FROM forums, fs WHERE fs.parent=forums.id)
    	SELECT * FROM tags
    	WHERE tags.forum in (SELECT id FROM fs)
    	ORDER BY id;    	
    	""",(forum_id,)).fetchall()
    return tags 

def forum_path(forum_id):
    db = get_db()
    ancestors = db.execute("""
        WITH RECURSIVE fs AS
            (SELECT * FROM forums WHERE id = ?
             UNION ALL
             SELECT forums.* FROM forums, fs WHERE fs.parent=forums.id)
        SELECT * FROM fs;
        """,(forum_id,)).fetchall()
    ancestors.reverse()
    return ancestors

@bp.route("/<int:forum_id>")
def view_forum(forum_id):
    db = get_db()
    forum = db.execute("SELECT * FROM forums WHERE id = ?",(forum_id,)).fetchone()
    threads = db.execute(
        """SELECT
            threads.id, threads.title, threads.creator, threads.created,
            threads.updated, threads.poll, number_of_posts.num_replies,
            most_recent_posts.created as mrp_created,
            most_recent_posts.author as mrp_author,
            most_recent_posts.id as mrp_id,
            most_recent_posts.content as mrp_content
        FROM threads
        INNER JOIN most_recent_posts ON most_recent_posts.thread = threads.id
        INNER JOIN number_of_posts ON number_of_posts.thread = threads.id
        WHERE threads.forum = ?
        ORDER BY threads.updated DESC;
        """,(forum_id,)).fetchall()
    thread_tags = {}
    thread_polls = {}

    avail_tags = get_avail_tags(forum_id)

    #todo: somehow optimise this
    for thread in threads:
        thread_tags[thread['id']] = db.execute(
            """SELECT tags.* FROM tags
            INNER JOIN thread_tags ON thread_tags.tag = tags.id
            WHERE thread_tags.thread = ?
            ORDER BY tags.id;
            """,(thread['id'],)).fetchall()

        if thread['poll'] is not None:
            # todo: make this not be duplicated from thread.py
            poll_row= db.execute("""
                SELECT polls.*,total_vote_counts.total_votes FROM polls
                LEFT OUTER JOIN total_vote_counts ON polls.id = total_vote_counts.poll
                WHERE polls.id = ?;                
                """,(thread['poll'],)).fetchone()
            options = db.execute("""
                SELECT poll_options.*, vote_counts.num
                FROM poll_options
                LEFT OUTER JOIN vote_counts  ON poll_options.poll = vote_counts.poll
                                            AND poll_options.option_idx = vote_counts.option_idx
                WHERE poll_options.poll = ?
                ORDER BY option_idx asc;
                """,(poll_row['id'],)).fetchall()

            poll = {}
            poll.update(poll_row)
            poll['options'] = options
            poll['total_votes']=poll['total_votes'] or 0
            thread_polls[thread['id']]=poll


    subforums_rows = db.execute("""
            SELECT max(threads.updated) as updated, forums.* FROM forums
            LEFT OUTER JOIN threads ON threads.forum=forums.id 
            WHERE parent = ?
            GROUP BY forums.id
            ORDER BY name ASC
            """,(forum_id,)).fetchall()
    subforums = []
    for s in subforums_rows:
        a={}
        a.update(s)
        if a['updated'] is not None:
            a['updated'] = datetime.datetime.fromisoformat(a['updated'])
        subforums.append(a)
        
    return render_template("view_forum.html",
            forum=forum,
            subforums=subforums,
            threads=threads,
            thread_tags=thread_tags,
            thread_polls=thread_polls,
            avail_tags=avail_tags,
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
        return redirect(url_for("forum.not_actual_index"))

    display_thread_id = [ True ] * len(results)
    last_thread = None
    for ix, result in enumerate(results):
        if result["thread"] == last_thread:
            display_thread_id[ix] = False
        last_thread = result["thread"]
    return render_template("search_results.html", results=results, query=query, display_thread_id=display_thread_id)
