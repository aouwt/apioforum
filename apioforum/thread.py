# view posts in thread

from flask import (
    Blueprint, render_template, abort, request, g, redirect,
    url_for, flash
)
from .db import get_db
from .mdrender import render

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
        rendered_posts = [render(q['content']) for q in posts]
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

@bp.route("/delete_post/<int:post_id>", methods=["GET","POST"])
def delete_post(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?",(post_id,)).fetchone()
    if post is None:
        flash("that post doesn't exist")
        return redirect("/")
    if post['author'] != g.user:
        flash("you can only delete posts that you created")
        return redirect(url_for("thread.view_thread",thread_id=post["thread"]))
    if request.method == "POST":
        # todo: don't actually delete, just mark as deleted or something (and wipe content)
        # so that you can have a "this post was deleted" thing
        db.execute("DELETE FROM posts WHERE id = ?",(post_id,))
        db.commit()
        flash("post deleted deletedly")
        return redirect(url_for("thread.view_thread",thread_id=post["thread"]))
    else:
        return render_template("delete_post.html",post=post,rendered_content=render_md(post["content"]))
        

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
            print("a")
            db.execute(
                "UPDATE posts SET content = ?, edited = 1, updated = current_timestamp WHERE id = ?",(newcontent,post_id))
            db.commit()
            flash("post edited editiously")
            return redirect(url_for("thread.view_thread",thread_id=post['thread']))
        else:
            flash(err)
    return render_template("edit_post.html",post=post)
            

