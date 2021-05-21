# boilerplate boilerplate boilerplate
# yay

from flask import Flask
from .db import get_db
import os

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, 'database.db'),
    )
    app.config.from_pyfile("config.py",silent=True)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    @app.route("/")
    def main():
        return "the"

    @app.route("/b")
    def b():
        db=get_db()
        return str(db.execute("select 2 + 2;").fetchone()[0])

    return app
