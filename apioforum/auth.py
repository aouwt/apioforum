from flask import (
    Blueprint, session, request, url_for, render_template, redirect,
    flash, 
)
from .db import get_db
    

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login",methods=('GET','POST'))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        err = None
        if not username:
            err = "Username required"
        elif not password:
            err = "Password required"
        elif username != "bee" or password != "form":
            err = "Invalid login"

        if err is None:
            session.clear()
            session['user'] = 'bee'
            return redirect(url_for('auth.cool'))

        flash(err)
        
    return render_template("auth/login.html.j2")


@bp.route("/cool")
def cool():
    user = session.get("user")
    if user is None:
        return "you are not logged in"
    else:
        return f"you are logged in as {user}"
