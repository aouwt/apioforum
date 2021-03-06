
from .db import get_db
from .permissions import is_admin

permissions = [
    "p_create_threads",
    "p_reply_threads",
    "p_manage_threads",
    "p_delete_posts",
    "p_view_threads",
    "p_vote",
    "p_create_polls",
    "p_approve",
    "p_create_subforum",
    "p_view_forum"
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
            """,(fid,)).fetchone()['parent']
    if the == None:
        if role == "other":
            raise(RuntimeError(
                "unable to find permissions for role 'other', " +
                "which should have associated permissions in all contexts."))
        else:
            return get_role_config(forum_id, "other")
    return the

def get_user_role(forum_id, username):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?',
            (username,)).fetchone()
    if user == None: return "other"
    if user['admin']: return "bureaucrat"
    
    fid = forum_id
    the = None
    while fid != None:
        r = db.execute("""
            SELECT * FROM role_assignments
            WHERE forum = ? AND user = ?;
            """,(fid,username)).fetchone()
        # the user's role is equal to the role assignnment of the closest 
        # ancestor unless the user's role is "bureaucrat" in any ancestor
        # in which case, the users role is "bureaucrat"
        if the == None or (r and r['role'] == "bureaucrat"):
            the = r
        fid = db.execute("""
            SELECT * FROM forums WHERE id = ?
            """,(fid,)).fetchone()['parent']
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

def has_permission(forum_id, username, permission, login_required=True):
    db = get_db()
    forum = db.execute("SELECT * FROM forums WHERE id = ?",(forum_id,)).fetchone()
    user = db.execute('SELECT * FROM users WHERE username = ?',
            (username,)).fetchone() if username else None

    if forum['unlisted'] and not (user and user['admin']): return False
    if username == None and login_required: return False

    role = get_user_role(forum_id, username) if username else "other"
    if role == "bureaucrat": return True
    config = get_role_config(forum_id, role)
    return config[permission]

def is_bureaucrat(forum_id, user):
    if user == None: return False
    return get_user_role(forum_id, user) == "bureaucrat"
