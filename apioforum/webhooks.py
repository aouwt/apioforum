import urllib
import abc
import json
from .db import get_db
from flask import url_for, flash

def abridge_post(text):
    MAXLEN = 20
    if len(text) > MAXLEN+3:
        return text[:MAXLEN]+"..."
    else:
        return text

webhook_types = {}
def webhook_type(t):
    def inner(cls):
        webhook_types[t] = cls
        return cls
    return inner

class WebhookType(abc.ABC):
    def __init__(self, url):
        self.url = url

    @abc.abstractmethod
    def on_new_thread(self,thread):
        pass
    @abc.abstractmethod
    def on_new_post(self,post):
        pass

def get_webhooks(forum_id):
    db = get_db()
    # todo inheritance (if needed)
    webhooks = db.execute("select * from webhooks where webhooks.forum = ?;",(forum_id,)).fetchall()

    for wh in webhooks:
        wh_type = wh['type']
        if wh_type not in webhook_types:
            print(f"unknown webhook type {wh_type}")
            continue
        wh_url = wh['url']
        wo = webhook_types[wh_type](wh_url)
        yield wo

def do_webhooks_thread(forum_id,thread):
    for wh in get_webhooks(forum_id):
        wh.on_new_thread(thread)
def do_webhooks_post(forum_id,post):
    for wh in get_webhooks(forum_id):
        wh.on_new_post(post)

@webhook_type("fake")
class FakeWebhook(WebhookType):
    def on_new_post(self, post):
        print(f'fake wh {self.url} post {post["id"]}')
    def on_new_thread(self, thread):
        print(f'fake wh {self.url} thread {thread["id"]}')

@webhook_type("discord")
class DiscordWebhook(WebhookType):
    def send(self,payload):
        headers = {
            "User-Agent":"apioforum (https://g.gh0.pw/apioforum, v0.0)",
            "Content-Type":"application/json",
        }
        req = urllib.request.Request(
            self.url,
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

    @staticmethod
    def field(name,value):
        return {"name":name,"value":value,"inline":True}

    def on_new_thread(self,thread):
	    f = self.field
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
	                "title":"new thread: "+thread['title'],
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
	    self.send(payload)

    def on_new_post(self,post):
	    from .thread import post_jump
	    f = self.field
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
	    self.send(payload)

    
