# boilerplate boilerplate boilerplate
# yay

from flask import Flask, request
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
    from . import permissions
    permissions.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import forum
    app.register_blueprint(forum.bp)

    from . import thread
    app.register_blueprint(thread.bp)

    from .fuzzy import fuzzy
    app.jinja_env.filters['fuzzy']=fuzzy

    @app.context_processor
    def path_for_next():
        p = request.path
        if len(request.query_string) > 0:
            p += "?" + request.query_string.decode("utf-8")
        return dict(path_for_next=p)
    

    app.add_url_rule("/",endpoint="index")

    return app
