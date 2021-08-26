import urllib
import json
from .db import get_db
from flask import url_for, flash

def abridge_post(text):
    MAXLEN = 20
    if len(text) > MAXLEN+3:
        return text[:MAXLEN]+"..."
    else:
        return text

def send_discord_webhook(url,payload):
    headers = {
        "User-Agent":"apioforum (https://f.gh0.pw/apioforum/, v0.0)",
        "Content-Type":"application/json",
    }
    req = urllib.request.Request(
        url,
        json.dumps(payload).encode("utf-8"),
        headers
    )
    # todo: read response and things
    urllib.request.urlopen(req)
    #try:
    #    res = urllib.request.urlopen(req)
    #except urllib.error.HTTPError as e:
    #    print(f"error {e.code} {e.read()}")
    #else:
    #    print(f"succ {res.read()}")
    
# todo: object oriented thing for different kinds of webhook (not just discord)

def f(name,value):
    # discord embed field
    return {"name":name,"value":value,"inline":True}

def discord_on_new_thread(wh_url, thread):
    db = get_db()
    forum = db.execute("select * from forums where id = ?",(thread['forum'],)).fetchone()
    username = thread['creator']
    userpage = url_for('user.view_user',username=username,_external=True)

    forumpage = url_for('forum.view_forum',forum_id=forum['id'],_external=True)

    post = db.execute("select * from posts where thread = ? order by id asc limit 1",(thread['id'],)).fetchone()
    
    
    payload = {
        "username":"apioforum",
        "avatar_url":"https://d.gh0.pw/lib/exe/fetch.php?media=wiki:logo.png",
        "embeds":[
            {
                "title":thread['title'],
                "description":abridge_post(post['content']),
                "url": url_for('thread.view_thread',thread_id=thread['id'],_external=True),
                "color": 0xff00ff,
                "fields":[
                    f('author',f"[{username}]({userpage})"),
                    f('forum',f"[{forum['name']}]({forumpage})"),
                ],
                "footer":{
                    "text":thread['created'].isoformat(' '),
                },
            },
        ],
    }
    send_discord_webhook(wh_url,payload)

def discord_on_new_post(wh_url, post):
    from .thread import post_jump
    db = get_db()

    thread = db.execute("select * from threads where id = ?",(post['thread'],)).fetchone()
    threadpage = url_for('thread.view_thread',thread_id=thread['id'],_external=True)

    forum = db.execute("select * from forums where id = ?",(thread['forum'],)).fetchone()
    forumpage = url_for('forum.view_forum',forum_id=forum['id'],_external=True)

    username = post['author']
    userpage = url_for('user.view_user',username=username,_external=True)

    payload = {
        "username":"apioforum",
        "avatar_url":"https://d.gh0.pw/lib/exe/fetch.php?media=wiki:logo.png",
        "embeds":[
            {
                "title":"re: "+thread['title'],
                "description":abridge_post(post['content']),
                "url": post_jump(post['id'],external=True),
                "color": 0x00ffff,
                "fields":[
                    f('author',f"[{username}]({userpage})"),
                    f('thread',f"[{thread['title']}]({threadpage})"),
                    f('forum',f"[{forum['name']}]({forumpage})"),
                ],
                "footer":{
                    "text":post['created'].isoformat(' '),
                },
            },
        ],
    }
    send_discord_webhook(wh_url,payload)

def _do_webhooks(forum_id,thing,fn):
    db = get_db()
    # todo inheritance
    webhooks = db.execute("select * from webhooks where forum = ? and type = 'discord'",(forum_id,)).fetchall()
    for wh in webhooks:
        wh_url = wh['url']
        try:
            fn(wh_url,thing)
        except:
            pass # handle probably
        flash(f"wh {wh['id']}")

def do_webhooks_thread(forum_id,thread):
    _do_webhooks(forum_id,thread,discord_on_new_thread)

def do_webhooks_post(forum_id,post):
    _do_webhooks(forum_id,post,discord_on_new_post)
    
    
