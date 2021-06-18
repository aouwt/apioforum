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

    from . import forum
    app.register_blueprint(forum.bp)

    from . import thread
    app.register_blueprint(thread.bp)

    from .util import fuzzy, rss_datetime
    app.jinja_env.filters["fuzzy"]=fuzzy
    app.jinja_env.filters["rss_datetime"]=rss_datetime

    app.add_url_rule("/",endpoint="index")

    return app
