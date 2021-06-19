# user pages

from flask import (
    Blueprint, render_template, abort, g, flash, redirect, url_for, request
)

from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db
from .mdrender import render

bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route("/<username>")
def view_user(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?;",(username,)).fetchone()
    if user is None:
        abort(404)
    posts = db.execute(
            "SELECT * FROM posts WHERE author = ? ORDER BY created DESC LIMIT 25;",(username,)).fetchall()
    rendered_posts = [render(post['content']) for post in posts]
    return render_template("view_user.html", 
            user=user, 
            rendered_bio=render(user['bio'] or "hail GEORGE"), 
            posts=posts,
            rendered_posts=rendered_posts)

@bp.route("/<username>/edit", methods=["GET","POST"])
def edit_user(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?;",(username,)).fetchone()
    if user is None:
        abort(404)
    if username != g.user:
        flash("you cannot modify other people")
        return redirect(url_for("user.view_user",username=username))

    if request.method == "POST":
        err = []
        if 'do_chpass' in request.form:
            if not check_password_hash(user['password'],request.form['password']):
                err.append("entered password does not match current password")
            else:
                db.execute("update users set password = ? where username = ?", 
                        (generate_password_hash(request.form["new_password"]), username))
                db.commit()
                flash("password changed changefully")
        if 'do_chbio' in request.form:
            if len(request.form['bio'].strip()) == 0:
                err.append("please submit nonempty bio")
            elif len(request.form['bio']) > 4000:
                err.append("bio is too long!!")
            else:
                db.execute("update users set bio = ? where username = ?", (request.form['bio'], username))
                db.commit()
                flash("bio updated successfully")

        if len(err) > 0:
            for e in err:
                flash(e)
        else:
            return redirect(url_for("user.view_user",username=username))
        
    return render_template("user_settings.html",user=user)
