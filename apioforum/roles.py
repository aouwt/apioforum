
from .db import get_db

permissions = [
    "p_create_threads",
    "p_reply_threads",
    "p_manage_threads",
    "p_view_threads",
    "p_vote",
    "p_create_polls",
    "p_approve",
    "p_create_subforum"
]

def get_role_config(forum_id, role):
    db = get_db()

    fid = forum_id
    the = None
    while the == None and fid != None:
        the = db.execute("""
            SELECT * FROM role_config 
            WHERE forum = ? AND role = ?;
            """, (fid,role)).fetchone()
        fid = db.execute("""
            """).fetchone()['parent']
