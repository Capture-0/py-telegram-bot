#!/usr/bin/env python3
import telebot
from myutils import *
import json
import re
import jsonpickle

CONF = j("conf.json")
TOKEN = CONF["TOKEN"]
DATABASE = CONF["DB"]
MAP = CONF["MAP"]
db = Database()
db.connect('data.db')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=["text", "photo", "audio"])
def update_received(msg):
    u = None
    uid = msg.chat.id
    markup = None
    try:
        u = User(uid)
    except:
        db.execute("insert into users (user_id) values (?)", (uid,))
        u = User(uid)
    u.last_message = jsonpickle.encode(msg)
    t = Tree(j(MAP), u)
    ires = t.process(msg).input()
    if ires != None:
        if ires[0] == "@":
            t.route(ires[1:])
        else:
            t.next(ires)
    newnode_callback(t)
    markup = t.process(msg).markup()
    u.send_message(t.process(msg).output(), markup)
    if type(t.current["next"]) == str:
        t.next()
        newnode_callback(t)
        markup = t.process(msg).markup()
        u.send_message(t.process(msg).output(), markup)

bot.polling(skip_pending = True, non_stop = True)


