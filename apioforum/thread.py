# view posts in thread

import itertools

from flask import (
    Blueprint, render_template, abort, request, g, redirect,
    url_for, flash, jsonify
)
from .db import get_db, DbWrapper
from .roles import has_permission, requires_permission
from .forum import Forum, Tag
from .user import User

bp = Blueprint("thread", __name__, url_prefix="/thread")

class Poll(DbWrapper):
    table = "polls"

    @classmethod
    def get_row(cls, key):
        db = get_db()
        row = db.execute("""
            SELECT polls.*,total_vote_counts.total_votes FROM polls
            LEFT OUTER JOIN total_vote_counts ON polls.id = total_vote_counts.poll
            WHERE polls.id = ?;                
            """,(key,)).fetchone()
        if row == None:
            return None
        options = db.execute("""
            SELECT poll_options.*, vote_counts.num
            FROM poll_options
            LEFT OUTER JOIN vote_counts  ON poll_options.poll = vote_counts.poll
                                        AND poll_options.option_idx = vote_counts.option_idx 
            WHERE poll_options.poll = ?
            ORDER BY option_idx asc;
            """,(key,)).fetchall()
        row['options'] = options

class PollOption(DbWrapper):
    table = "poll_options"
    primary_key = None
    references = {"poll": Poll}

class Vote(DbWrapper):
    table = "votes"
    references = {"poll": Poll, "user": User}

class Thread(DbWrapper):
    table = "threads"
    references = {"forum": Forum, "poll": Poll}

    def get_posts(self):
        return Post.query_some("""
            SELECT * FROM posts
            WHERE thread = ?
            ORDER BY created ASC;
            """,(self,))

    def get_tags(self):
        return Tag.query_some("""
            SELECT tags.* FROM tags
            INNER JOIN thread_tags ON thread_tags.tag = tags.id
            ORDER BY tags.id
            """,(self,))

    def get_forum(self):
        return self.forum

class Post(DbWrapper):
    table = "posts"
    references = {"thread": Thread, "author": User, "vote": Vote}


def post_jump(thread_id, post_id):
    return url_for("thread.view_thread",thread_id=thread_id)+"#post_"+str(post_id)

@bp.route("/<db(Thread):thread>")
@requires_permission("p_view_threads")
def view_thread(thread):
    db = get_db()
    posts = thread.get_posts()
    tags = thread.get_tags()

    if g.user is None or thread.poll is None:
        has_voted = None
    else:
        v = Vote.query_one("""
            SELECT * FROM votes 
            WHERE poll = ? 
                AND user = ? 
                AND current 
                AND NOT is_retraction;
            """,(thread.poll,g.user))
        has_voted = v is not None
        
    return render_template(
        "view_thread.html",
        posts=posts,
        thread=thread,
        tags=tags,
        has_voted=has_voted,
    )

def register_vote(thread,pollval):
    if pollval is None or pollval == 'dontvote':
        return
        
    is_retraction = pollval == 'retractvote'

    if is_retraction:
        option_idx = None
    else:
        option_idx = int(pollval)
        
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE votes
        SET current = 0
        WHERE poll = ? AND user = ?;
    """,(thread['poll'],g.user))

    cur.execute("""
        INSERT INTO votes (user,poll,option_idx,time,current,is_retraction)
        VALUES (?,?,?,current_timestamp,1,?);
        """,(g.user,thread['poll'],option_idx,is_retraction))
    vote_id = cur.lastrowid
    return vote_id

@bp.route("/<int:thread_id>/create_poll",methods=["POST"])
def create_poll(thread_id):
    fail = redirect(url_for('thread.config_thread',thread_id=thread_id))
    success = redirect(url_for('thread.view_thread',thread_id=thread_id))
    err = None
    db = get_db()
    thread = db.execute('select * from threads where id = ?',(thread_id,)).fetchone()

    polltitle = request.form.get('polltitle','').strip()
    polloptions = [q.strip() for q in request.form.get('polloptions','').split("\n") if len(q.strip()) > 0]

    if thread is None:
        err = "that thread does not exist"
    elif g.user is None:
        err = "you need to be logged in to do that"
    elif g.user != thread['creator'] and \
            not has_permission(thread['forum'],g.user,"p_manage_threads"):
        err = "you can only create polls on threads that you own"
    elif thread['poll'] is not None:
        err = "a poll already exists for that thread"
    elif not len(polltitle) > 0:
        err = "poll title can't be empty"
    elif len(polloptions) < 2:
        err = "you must provide at least 2 options"
    elif not has_permission(thread['forum'], g.user, "p_create_polls"):
        err = "you do not have permission to do that"

    if err is not None:
        flash(err)
        return fail
    else:
        cur = db.cursor()
        cur.execute("INSERT INTO polls (title) VALUES (?)",(polltitle,))
        pollid = cur.lastrowid
        cur.execute("UPDATE threads SET poll = ? WHERE threads.id = ?",(pollid,thread_id))
        cur.executemany(
            "INSERT INTO poll_options (poll,option_idx,text) VALUES (?,?,?)",
            zip(itertools.repeat(pollid),itertools.count(1),polloptions)
        )
        db.commit()
        flash("poll created successfully")
        return success

@bp.route("/<int:thread_id>/delete_poll",methods=["POST"])
def delete_poll(thread_id):
    fail = redirect(url_for('thread.config_thread',thread_id=thread_id))
    success = redirect(url_for('thread.view_thread',thread_id=thread_id))
    err = None
    db = get_db()
    thread = db.execute('select * from threads where id = ?',(thread_id,)).fetchone()

    if thread is None:
        err = "that thread does not exist"
    elif g.user is None:
        err = "you need to be logged in to do that"
    elif g.user != thread['creator'] and not \
            has_permission(thread['forum'], g.user, "p_manage_threads"):
        err = "you can only delete polls on threads that you own"
    elif thread['poll'] is None:
        err = "there is no poll to delete on this thread"

    if err is not None:
        flash(err)
        return fail
    else:
        pollid = thread['poll']
        db.execute("UPDATE posts SET vote = NULL WHERE thread = ?",(thread_id,)) # this assumes only max one poll per thread 
        db.execute("DELETE FROM votes WHERE poll = ?",(pollid,))
        db.execute("DELETE FROM poll_options WHERE poll = ?",(pollid,))
        db.execute("UPDATE THREADS set poll = NULL WHERE id = ?",(thread_id,))
        db.execute("DELETE FROM polls WHERE id = ?",(pollid,))
        db.commit()
        flash("poll deleted successfully")
        return success
        
@bp.route("/<int:thread_id>/create_post", methods=("POST",))
def create_post(thread_id):
    if g.user is None:
        flash("you need to log in before you can post")
    db = get_db()
    content = request.form['content']
    thread = db.execute("SELECT * FROM threads WHERE id = ?;",(thread_id,)).fetchone()
    if len(content.strip()) == 0:
        flash("you cannot post an empty message")
    elif not thread:
        flash("that thread does not exist")
    elif not has_permission(thread['forum'], g.user, "p_reply_threads"):
        flash("you do not have permission to do this")
    elif not has_permission(thread['forum'], g.user, "p_view_threads"):
        flash("you do not have permission to do this")
    elif not has_permission(thread['forum'], g.user, "p_vote") \
            and 'poll' in request.form:
        flash("you do not have permission to do this")
    else:
        vote_id = None
        if thread['poll'] is not None:
            pollval = request.form.get('poll')
            try:
                vote_id = register_vote(thread,pollval)
            except ValueError:
                flash("invalid poll form value")
                return redirect(url_for('thread.view_thread',thread_id=thread_id))

        cur = db.cursor()
        cur.execute("""
            INSERT INTO posts (thread,author,content,created,vote)
            VALUES (?,?,?,current_timestamp,?);
            """,(thread_id,g.user,content,vote_id))
        post_id = cur.lastrowid
        cur.execute(
            "UPDATE threads SET updated = current_timestamp WHERE id = ?;",
            (thread_id,)
        )
        db.commit()
        flash("post posted postfully")
        return redirect(post_jump(thread_id, post_id))
    return redirect(url_for('thread.view_thread',thread_id=thread_id))

@bp.route("/delete_post/<int:post_id>", methods=["GET","POST"])
def delete_post(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?",(post_id,)).fetchone()
    thread = db.execute("SELECT * FROM threads WHERE id = ?",(post['thread'],)).fetchone()
    if post is None:
        flash("that post doesn't exist")
        return redirect("/")
    if post['author'] != g.user and not has_permission(thread['forum'], g.user, "p_delete_posts"):
        flash("you do not have permission to do that")
        return redirect(url_for("thread.view_thread",thread_id=post["thread"]))
    if request.method == "POST":
        db.execute("""
            UPDATE posts SET 
                content = '',
                deleted = 1
            WHERE id = ?""",(post_id,))
        db.commit()
        flash("post deleted deletedly")
        return redirect(url_for("thread.view_thread",thread_id=post["thread"]))
    else:
        return render_template("delete_post.html",post=post)
        
@bp.route("/delete_thread/<int:thread_id>", methods=["GET","POST"])
def delete_thread(thread_id):
    db = get_db()
    thread = db.execute("SELECT * FROM threads WHERE id = ?",(thread_id,)).fetchone()
    if thread is None:
        flash("that thread doesn't exist")
        return redirect("/")
    if not has_permission(thread['forum'], g.user, "p_delete_posts"):
        flash("you do not have permission to do that")
        return redirect(url_for("thread.view_thread",thread_id=thread_id))
    if request.method == "POST":
        db.execute("DELETE FROM posts WHERE thread = ?",(thread_id,))
        db.execute("DELETE FROM threads WHERE id = ?",(thread_id,))
        db.commit()
        flash("thread deleted deletedly")
        return redirect(url_for("forum.view_forum",forum_id=thread['forum']))
    else:
        count = db.execute("SELECT num_replies FROM number_of_posts WHERE thread = ?",
                (thread_id,)).fetchone()[0]
        return render_template("delete_thread.html",thread=thread,post_count=count)
        

@bp.route("/edit_post/<int:post_id>",methods=["GET","POST"])
def edit_post(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?",(post_id,)).fetchone()
    if post is None:
        flash("that post doesn't exist")
        return redirect(url_for('index'))

    if post['author'] != g.user:
        flash("you can only edit posts that you created")
        return redirect(url_for("thread.view_thread",thread_id=post['thread']))
    # note: i am writing this while i am very tired, so probably
    # come back and test this properly later
    if request.method == "POST":
        err = None 
        newcontent = request.form['newcontent']
        if len(newcontent.strip()) == 0:
            err="post contents can't be empty"
        print(err)
        if err is None:
            db.execute(
                "UPDATE posts SET content = ?, edited = 1, updated = current_timestamp WHERE id = ?",(newcontent,post_id))
            db.commit()
            flash("post edited editiously")
            return redirect(post_jump(post['thread'],post_id))
        else:
            flash(err)
    return render_template("edit_post.html",post=post)

@bp.route("/view_post/<int:post_id>")
def view_post(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?",(post_id,)).fetchone()
    if post is None:
        flash("that post doesn't exist")
        return redirect(url_for('index'))

    # when we have permissions, insert permissions check here
    return render_template("view_post.html",post=post)
    
    
            
@bp.route("/<int:thread_id>/config",methods=["GET","POST"])
def config_thread(thread_id):
    db = get_db()
    thread = db.execute("select * from threads where id = ?",(thread_id,)).fetchone()
    thread_tags = [r['tag'] for r in db.execute("select tag from thread_tags where thread = ?",(thread_id,)).fetchall()]
    avail_tags = get_avail_tags(thread['forum'])
    err = None
    if g.user is None:
        err = "you need to be logged in to do that"
    elif not has_permission(thread['forum'], g.user, "p_view_threads"):
        err = "you do not have permission to do that"
    elif g.user != thread['creator'] and not has_permission(thread['forum'], g.user, "p_manage_threads"):
        err = "you can only configure threads that you own"

    if err is not None:
        flash(err)
        return redirect(url_for("thread.view_thread",thread_id=thread_id))

    if request.method == "POST":
        err = []
        if request.form['title'] != thread['title']:
            title = request.form['title']
            if len(title.strip()) == 0:
                err.append("title can't be empty")
            else:
                db.execute("update threads set title = ? where id = ?;",(title,thread_id))
                flash("title updated successfully")
                db.commit()
        changed = False
        for avail_tag in avail_tags:
            tagid = avail_tag['id']
            current = tagid in thread_tags
            wanted  = f'tag_{tagid}' in request.form
            if wanted and not current:
                db.execute("insert into thread_tags (thread, tag) values (?,?)",(thread_id,tagid))
                changed = True
            elif current and not wanted:
                db.execute("delete from thread_tags where thread = ? and tag = ?",(thread_id,tagid))
                changed = True
        if changed:
            db.commit()
            flash("tags updated successfully")

        if len(err) > 0:
            for e in err:
                flash(e)
        else:
            return redirect(url_for("thread.view_thread",thread_id=thread_id))
            

    return render_template("config_thread.html", thread=thread,thread_tags=thread_tags,avail_tags=avail_tags)
    
