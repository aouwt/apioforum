# user pages

from flask import (
    Blueprint, render_template, abort, g
)

from .db import get_db
from .mdrender import render

bp = Blueprint("user", __name__, url_prefix="/user")

@bp.route("/<username>")
def view_user(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?;",(username,)).fetchone()
    if user is None:
        abort(404)
    return render_template("view_user.html", 
            user=user, rendered_bio=render(user['bio'] or "hail GEORGE"))
