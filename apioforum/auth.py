from flask import (
    Blueprint, session, request, url_for, render_template, redirect,
    flash, g
)
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db
import functools

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login",methods=('GET','POST'))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        err = None
        user = db.execute(
            "SELECT password FROM users WHERE username = ?;",(username,)
        ).fetchone()
        if not username:
            err = "username required"
        elif not password:
            err = "password required"
        elif user is None or not check_password_hash(user['password'], password):
            err = "invalid login"

        if err is None:
            session.clear()
            session['user'] = username
            return redirect(url_for('auth.cool'))

        flash(err)
        
    return render_template("auth/login.html.j2")

@bp.route("/register", methods=("GET","POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        err = None
        if not username:
            err = "Username required"
        elif not password:
            err = "Password required"
        elif db.execute(
            "SELECT 1 FROM users WHERE username = ?;", (username,)
        ).fetchone() is not None:
            err = f"User {username} is already registered."

        if err is None:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?,?);",
                (username,generate_password_hash(password))
            )
            db.commit()
            flash("successfully created account")
            session['user'] = username
            return redirect(url_for("auth.cool"))

        flash(err)
            
    return render_template("auth/register.html.j2")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.cool"))

@bp.before_app_request
def load_user():
    username = session.get("user")
    if username is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE username = ?;", (username,)
        ).fetchone()

def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        print(g.user)
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped

@bp.route("/cool")
def cool():
    user = session.get("user")
    if user is None:
        return "you are not logged in"
    else:
        return f"you are logged in as {user}"

@bp.route("/cooler")
@login_required
def cooler():
    return "bee"
