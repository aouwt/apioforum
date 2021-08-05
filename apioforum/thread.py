# view posts in thread

from flask import (
    Blueprint, render_template, abort, request, g, redirect,
    url_for, flash
)
from .db import get_db
from .roles import has_permission

bp = Blueprint("thread", __name__, url_prefix="/thread")

def post_jump(thread_id, post_id):
    return url_for("thread.view_thread",thread_id=thread_id)+"#post_"+str(post_id)

@bp.route("/<int:thread_id>")
def view_thread(thread_id):
    db = get_db()
    thread = db.execute("SELECT * FROM threads WHERE id = ?;",(thread_id,)).fetchone()
    if thread is None:
        abort(404)
    if not has_permission(thread['forum'], g.user, "p_view_threads"):
        abort(403)
    posts = db.execute(
        "SELECT * FROM posts WHERE thread = ? ORDER BY created ASC;",
        (thread_id,)
    ).fetchall()
    tags = db.execute(
        """SELECT tags.* FROM tags
        INNER JOIN thread_tags ON thread_tags.tag = tags.id
        WHERE thread_tags.thread = ?
        ORDER BY tags.id""",(thread_id,)).fetchall()
    return render_template("view_thread.html",posts=posts,thread=thread,tags=tags)

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
    else:
        cur = db.cursor()
        cur.execute(
            "INSERT INTO posts (thread,author,content,created) VALUES (?,?,?,current_timestamp);",
            (thread_id,g.user,content)
        )
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
        return redirect(url_for("thread.view_thread",thread_id=post["thread"]))
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
        # todo: index route
        return redirect("/")

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
            
@bp.route("/<int:thread_id>/config",methods=["GET","POST"])
def config_thread(thread_id):
    db = get_db()
    thread = db.execute("select * from threads where id = ?",(thread_id,)).fetchone()
    thread_tags = [r['tag'] for r in db.execute("select tag from thread_tags where thread = ?",(thread_id,)).fetchall()]
    avail_tags = db.execute("select * from tags order by id").fetchall()
    err = None
    if g.user is None:
        err = "you need to be logged in to do that"
    elif g.user != thread['creator'] and not has_permission(thread['forum'], g.user, "g_manage_threads"):
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
        wanted_tags = []
        for tagid in range(1,len(avail_tags)+1):
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
    
