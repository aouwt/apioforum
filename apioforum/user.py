# user pages

from flask import (
    Blueprint, render_template, abort, g, flash, redirect, url_for, request
)

from werkzeug.security import check_password_hash, generate_password_hash
from .db import DbWrapper, get_db

bp = Blueprint("user", __name__, url_prefix="/user")

class User(DbWrapper):
    table = "users"
    primary_key = "username"
    
    def set_password(self, password):
        self.password = generate_password_hash(password)


@bp.route("/<username>")
def view_user(username):
    db = get_db()
    try:
        user = User.fetch(username)
    except KeyError:
        abort(404)
    posts = db.execute("""
        SELECT * FROM posts
        WHERE author = ? AND deleted = 0
        ORDER BY created DESC 
        LIMIT 25;""",(user,)).fetchall()
    return render_template("view_user.html", user=user, posts=posts)

@bp.route("/<username>/edit", methods=["GET","POST"])
def edit_user(username):
    try:
        user = User.fetch(username)
    except KeyError:
        abort(404)
    if username != g.user:
        flash("you cannot modify other people")
        return redirect(url_for("user.view_user",username=username))

    db = get_db()
    if request.method == "POST":
        err = []
        if len(request.form['new_password']) > 0:
            if not check_password_hash(user.password,request.form['password']):
                err.append("entered password does not match current password")
            else:
                user.set_password(request.form['new_password'])
                db.commit()
                flash("password changed changefully")
        if request.form['bio'] != user.bio:
            if len(request.form['bio'].strip()) == 0:
                err.append("please submit nonempty bio")
            elif len(request.form['bio']) > 4500:
                err.append("bio is too long!!")
            else:
                user.bio = request.form['bio']
                db.commit()
                flash("bio updated successfully")

        if len(err) > 0:
            for e in err:
                flash(e)
        else:
            return redirect(url_for("user.view_user",username=username))
        
    return render_template("user_settings.html",user=user)
