# boilerplate boilerplate boilerplate
# yay

from flask import Flask
from .db import get_db

def create_app():
    app = Flask(__name__)

    from . import db
    db.init_app(app)

    @app.route("/")
    def main():
        return "the"

    @app.route("/b")
    def b():
        db=get_db()
        return str(db.execute("select 2 + 2;").fetchone()[0])

    return app
