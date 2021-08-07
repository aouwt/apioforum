# log in with apioforum

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for, flash, abort
)

from .db import get_db
from secrets import token_hex
from urllib.parse import urlparse

bp = Blueprint("api", __name__, url_prefix="/api")

@bp.route("/authorize")
def authorize():
    return "placeholder"
