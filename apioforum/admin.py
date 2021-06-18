from flask import (
    Blueprint, render_template
)
from .db import get_db
from .permissions import admin_required

bp = Blueprint("admin",__name__,url_prefix="/admin")

@bp.route("/")
@admin_required
def admin_page():
    db = get_db()
    admins = db.execute("select * from users where admin > 0;").fetchall()
    return render_template("admin/admin_page.html",admins=admins)
