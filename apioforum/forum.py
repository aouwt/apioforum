# view threads in a forum
# currently there is only ever one forum however

from flask import (
    Blueprint, render_template, request,
    g, redirect, url_for, flash, abort
)

from .db import get_db
from .mdrender import render
from .roles import get_forum_roles,has_permission,is_bureaucrat,get_user_role, permissions as role_permissions
from sqlite3 import OperationalError
import datetime
import functools

bp = Blueprint("forum", __name__, url_prefix="/")

@bp.route("/")
def not_actual_index():
    return redirect("/1")

def forum_path(forum_id):
    db = get_db()
    ancestors = db.execute("""
        WITH RECURSIVE fs AS
            (SELECT * FROM forums WHERE id = ?
             UNION ALL
             SELECT forums.* FROM forums, fs WHERE fs.parent=forums.id)
        SELECT * FROM fs;
        """,(forum_id,)).fetchall()
    ancestors.reverse()
    return ancestors

def forum_route(relative_path, **kwargs):
    def decorator(f):
        path = "/<int:forum_id>"
        if relative_path != "":
            path += "/" + relative_path

        @bp.route(path, **kwargs)
        @functools.wraps(f)
        def wrapper(forum_id, *args, **kwargs):
            db = get_db()
            forum = db.execute("SELECT * FROM forums WHERE id = ?",
                    (forum_id,)).fetchone()
            if forum == None:
                abort(404)
            return f(forum, *args, **kwargs)

    return decorator

def requires_permission(permission):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(forum, *args, **kwargs):
            if not has_permission(forum['id'], g.user, permission):
                abort(403)
            return f(forum, *args, **kwargs)
        return wrapper
    return decorator

def requires_bureaucrat(f):
    @functools.wraps(f)
    def wrapper(forum, *args, **kwargs):
        if not is_bureaucrat(forum['id'], g.user):
            abort(403)
        return f(forum, *args, **kwargs)
    return wrapper

@forum_route("")
def view_forum(forum):
    db = get_db()
    threads = db.execute(
        """SELECT
            threads.id, threads.title, threads.creator, threads.created,
            threads.updated, number_of_posts.num_replies,
            most_recent_posts.created as mrp_created,
            most_recent_posts.author as mrp_author,
            most_recent_posts.id as mrp_id,
            most_recent_posts.content as mrp_content,
            most_recent_posts.deleted as mrp_deleted
        FROM threads
        INNER JOIN most_recent_posts ON most_recent_posts.thread = threads.id
        INNER JOIN number_of_posts ON number_of_posts.thread = threads.id
        WHERE threads.forum = ?
        ORDER BY threads.updated DESC;
        """,(forum['id'],)).fetchall()
    thread_tags = {}
    #todo: somehow optimise this
    for thread in threads:
        thread_tags[thread['id']] = db.execute(
            """SELECT tags.* FROM tags
            INNER JOIN thread_tags ON thread_tags.tag = tags.id
            WHERE thread_tags.thread = ?
            ORDER BY tags.id;
            """,(thread['id'],)).fetchall()

    subforums_rows = db.execute("""
            SELECT max(threads.updated) as updated, forums.* FROM forums
            LEFT OUTER JOIN threads ON threads.forum=forums.id 
            WHERE parent = ?
            GROUP BY forums.id
            ORDER BY name ASC
            """,(forum['id'],)).fetchall()
    subforums = []
    for s in subforums_rows:
        a={}
        a.update(s)
        if a['updated'] is not None:
            a['updated'] = datetime.datetime.fromisoformat(a['updated'])
        subforums.append(a)
        
    return render_template("view_forum.html",
            forum=forum,
            subforums=subforums,
            threads=threads,
            thread_tags=thread_tags,
            )

@forum_route("create_thread",methods=("GET","POST"))
def create_thread(forum):
    db = get_db()
    forum = db.execute("SELECT * FROM forums WHERE id = ?",(forum['id'],)).fetchone()
    if forum is None:
        flash("that forum doesn't exist")
        return redirect(url_for('index'))
    
    if g.user is None:
        flash("you need to be logged in to create a thread")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        title = request.form['title']
        content = request.form['content']
        err = None
        if len(title.strip()) == 0 or len(content.strip()) == 0:
            err = "title and content can't be empty"

        if err is None:
            cur = db.cursor()
            cur.execute(
                "INSERT INTO threads (title,creator,created,updated,forum) VALUES (?,?,current_timestamp,current_timestamp,?);",
                (title,g.user,forum['id'])
            )
            thread_id = cur.lastrowid
            cur.execute(
                "INSERT INTO posts (thread,created,author,content) VALUES (?,current_timestamp,?,?);",
                (thread_id,g.user,content)
            )
            db.commit()
            return redirect(url_for('thread.view_thread',thread_id=thread_id))
        flash(err)
        
        
    return render_template("create_thread.html")

@forum_route("roles",methods=("GET","POST"))
@requires_bureaucrat
def edit_roles(forum):
    db = get_db()
    role_configs = db.execute(
        "SELECT * FROM role_config WHERE forum = ? ORDER BY ID ASC",
        (forum['id'],)).fetchall()

    if request.method == "POST":
        for config in role_configs:
            if 'roleconfig_' + config['role'] in request.form:
                for p in role_permissions:
                    permission_setting =\
                        f"perm_{config['role']}_{p}" in request.form 
                    db.execute(f"""
                        UPDATE role_config SET {p} = ?
                            WHERE forum = ? AND role = ?;
                        """, 
                        (permission_setting,forum['id'], config['role']))
        db.commit()
        flash('roles sucessfully enroled')
        return redirect(url_for('forum.view_forum',forum_id=forum['id']))

    role_config_roles = [c['role'] for c in role_configs]
    other_roles = [role for role in get_forum_roles(forum['id']) if not role in role_config_roles]

    return render_template("edit_permissions.html",
            forum=forum,
            role_configs=role_configs,
            other_roles=other_roles
            )

@forum_route("roles/new",methods=["POST"])
def add_role(forum):
    name = request.form['role'].strip()
    if not all(c in (" ","-","_") or c.isalnum() for c in name) \
            or len(name) > 32:
        flash("role name must contain no special characters")
        return redirect(url_for('forum.edit_roles',forum_id=forum['id']))
    if name == "bureaucrat":
        flash("cannot configure permissions for bureaucrat")
        return redirect(url_for('forum.edit_roles',forum_id=forum['id']))

    db = get_db()

    existing_config = db.execute("""
        SELECT * FROM role_config WHERE forum = ? AND role = ?
        """,(forum['id'],name)).fetchone()
    if not existing_config:
        db.execute("INSERT INTO role_config (forum,role) VALUES (?,?)",
                (forum['id'],name))
        db.commit()
    return redirect(url_for('forum.edit_roles',forum_id=forum['id']))

@forum_route("role",methods=["GET","POST"])
@requires_permission("p_approve")
def view_user_role(forum):
    if request.method == "POST":
        return redirect(url_for( 'forum.edit_user_role',
            username=request.form['user'],forum_id=forum['id']))
    else:
        return render_template("role_assignment.html",forum=forum)

@forum_route("role/<username>",methods=["GET","POST"])
@requires_permission("p_approve")
def edit_user_role(forum, username):
    db = get_db()
    if request.method == "POST":
        user = db.execute("SELECT * FROM users WHERE username = ?;",(username,)).fetchone()
        if user == None:
            return redirect(url_for('forum.edit_user_role',
                username=username,forum_id=forum['id']))
        role = request.form['role']
        if role not in get_forum_roles(forum['id']) and role != "" and role != "bureaucrat":
            flash("no such role")
            return redirect(url_for('forum.edit_user_role',
                username=username,forum_id=forum['id']))
        if not is_bureaucrat(forum['id'],g.user) and role != "approved" and role != "":
            abort(403)
        existing = db.execute("SELECT * FROM role_assignments WHERE user = ?;",(username,)).fetchone()
        if existing:
            db.execute("DELETE FROM role_assignments WHERE user = ?;",(username,))
        if role != "":
            db.execute(
                "INSERT INTO role_assignments (user,role,forum) VALUES (?,?,?);",
                (username,role,forum['id']))
            db.commit()
        flash("role assigned assignedly")
        return redirect(url_for('forum.view_forum',forum_id=forum['id']))
    else:
        user = db.execute("SELECT * FROM users WHERE username = ?;",(username,)).fetchone()
        if user == None:
            return render_template("role_assignment.html",
                    forum=forum,user=username,invalid_user=True)
        r = db.execute(
                "SELECT role FROM role_assignments WHERE user = ?;",(username,)).fetchone()
        if not r:
            assigned_role = ""
        else:
            assigned_role = r[0]
        role = get_user_role(forum['id'], username)
        if is_bureaucrat(forum['id'], g.user):
            roles = get_forum_roles(forum['id'])
            roles.remove("other")
            roles.add("bureaucrat")
        else:
            roles = ["approved"]
        return render_template("role_assignment.html",
                forum=forum,user=username,role=role,
                assigned_role=assigned_role,forum_roles=roles)

@bp.route("/search")
def search():
    db = get_db()
    query = request.args["q"]
    try:
        results = db.execute("""
        SELECT posts.id, highlight(posts_fts, 0, '<mark>', '</mark>') AS 
            content, posts.thread, posts.author, posts.created, posts.edited, 
            posts.updated, threads.title AS thread_title
        FROM posts_fts
        JOIN posts ON posts_fts.rowid = posts.id
        JOIN threads ON threads.id = posts.thread
        WHERE posts_fts MATCH ?
        ORDER BY rank
        LIMIT 50
        """, (query,)).fetchall()
    except OperationalError:
        flash('your search query was malformed.')
        return redirect(url_for("forum.view_forum"))

    display_thread_id = [ True ] * len(results)
    last_thread = None
    for ix, result in enumerate(results):
        if result["thread"] == last_thread:
            display_thread_id[ix] = False
        last_thread = result["thread"]
    return render_template("search_results.html", results=results, query=query, display_thread_id=display_thread_id)
