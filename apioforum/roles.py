
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
    return db.execute("""
        SELECT * FROM role_config 
        WHERE forum = ? AND role = ?;
        """, (forum_id,role)).fetchone()

def overridden_perms(forum_id, role):
    db = get_db()
    p = {}
    for perm in permissions:
        p[perm] = False
    ancestors = db.execute("""
        WITH RECURSIVE fs AS
            (SELECT * FROM forums WHERE id = ?
             UNION ALL
             SELECT forums.* FROM forums, fs WHERE fs.parent=forums.id)
        SELECT * FROM fs;
        """,(forum_id,)).fetchall()[1:]
    for ancestor in ancestors:
        config = get_role_config(ancestor['id'], role)
        if config and config['inherit']:
            for perm in permissions:
                p[perm] = p[perm] or not config[perm]
    return p

def forum_perms(forum_id, role):
    role_config = get_role_config(forum_id, role)
    if not role_config:
        role_config = get_role_config(forum_id, "other")
    p = {}
    overridden = overridden_perms(forum_id, role)
    for perm in permissions:
        p[perm] = role_config[perm] and not overridden[perm]
