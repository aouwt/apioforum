# boilerplate boilerplate boilerplate
# yay

from flask import Flask, request, session, render_template
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

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

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

    from . import admin
    app.register_blueprint(admin.bp)

    from . import user
    app.register_blueprint(user.bp)

    from .fuzzy import fuzzy
    app.jinja_env.filters['fuzzy']=fuzzy

    from .util import gen_colour
    app.jinja_env.filters['gen_colour']=gen_colour

    @app.context_processor
    def path_for_next():
        p = request.path
        if len(request.query_string) > 0 and not p.startswith("/auth"):
            p += "?" + request.query_string.decode("utf-8")
        return dict(path_for_next=p)

    app.jinja_env.globals.update(forum_path=forum.forum_path)
    app.jinja_env.globals.update(post_jump=thread.post_jump)
    from .roles import has_permission, is_bureaucrat, get_user_role
    app.jinja_env.globals.update(
            has_permission=has_permission,
            is_bureaucrat=is_bureaucrat,
            get_user_role=get_user_role)

    from .mdrender import render
    @app.template_filter('md')
    def md_render(s):
        return render(s)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('err/404.html'), 404
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('err/403.html'), 403

    app.add_url_rule("/",endpoint="index")

    return app
