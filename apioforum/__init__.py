# boilerplate boilerplate boilerplate
# yay

from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def main():
        return "the"

    return app
