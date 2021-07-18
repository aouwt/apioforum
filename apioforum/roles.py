
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
            SELECT * FROM forums WHERE id = ?
            """(fid,)).fetchone()['parent']
    if the == None:
        if role == "other":
            raise(RuntimeError(
                "unable to find permissions for role 'other', " +
                "which should have associated permissions in all contexts."))
        else:
            return get_role_config(forum_id, "other")
    return the

def get_user_role(forum_id, user):
    db = get_db()
    
    fid = forum_id
    the = None
    while the == None and fid != None:
        the = db.execute("""
            SELECT * FROM role_assignments
            WHERE forum = ? AND user = ?;
            """, (fid,role)).fetchone()
        fid = db.execute("""
            SELECT * FROM forums WHERE id = ?
            """).fetchone()['parent']
    return the['role'] if the != None else 'other'

def get_forum_roles(forum_id):
    db = get_db()

    ancestors = db.execute("""
        WITH RECURSIVE fs AS
            (SELECT * FROM forums WHERE id = ?
             UNION ALL
             SELECT forums.* FROM forums, fs WHERE fs.parent=forums.id)
        SELECT * FROM fs;
        """,(forum_id,)).fetchall()
    configs = []
    for a in ancestors:
        configs += db.execute("""
            SELECT * FROM role_config WHERE forum = ?
            """,(a['id'],)).fetchall()
    return set(r['role'] for r in configs)
