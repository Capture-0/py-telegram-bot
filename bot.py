#!/usr/bin/env python3
import telebot
from myutils import *
import json
import re
import jsonpickle

TOKEN = "253284677:AAGH-nxJuBFmuHWY8RL4E49pHgP-pvWpUkI"
db = Database()
db.connect('data.db')
bot = telebot.TeleBot(TOKEN)

def sendmsg(id, msg, markup = None):
    if msg == None:
        return None
    if markup == None:
        bot.send_message(id,msg)
    else:
        bot.send_message(id,msg,reply_markup=markup)

@bot.message_handler(content_types=["text", "photo", "audio"])
def update_received(msg):
    u = None
    uid = msg.chat.id
    markup = None
    sm = lambda message: sendmsg(msg.chat.id, message, markup)
    try:
        u = User(uid)
    except:
        db.execute("insert into users (user_id) values (?)", (uid,))
        u = User(uid)
    u.last_message = jsonpickle.encode(msg)
    t = Tree(j("map.json"), u)
    ires = t.process(msg).input()
    if ires != None:
        if ires[0] == "@":
            t.route(ires[1:])
        else:
            t.next(ires)
    newnode_callback(t)
    markup = t.process(msg).markup()
    sm(t.process(msg).output())
    if type(t.current["next"]) == str:
        t.next()
        newnode_callback(t)
        markup = t.process(msg).markup()
        sm(t.process(msg).output())

bot.polling(skip_pending = True, non_stop = True)


