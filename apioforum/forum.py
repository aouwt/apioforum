# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template
)
from .db import get_db

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def view_forum():
    db = get_db()
    threads = db.execute("SELECT * FROM threads ORDER BY updated DESC LIMIT 10;").fetchall()
    return render_template("view_forum.html.j2",threads=threads)
