#!/usr/bin/env python3
# operations first arg abbr:
#     g: get column
#     s: set column
#     gd: get data
#     sd: set data
#     q: database query
#     e: execute a preset

# variables: wrapped in []
#     ID: user id
#     MSG: user text message
#     UPDATE: update object
#     FILE: update's file

import urllib.parse
import sys
from myutils import *
import json
import telebot

TOKEN = "253284677:AAGH-nxJuBFmuHWY8RL4E49pHgP-pvWpUkI"
bot = telebot.TeleBot(TOKEN)
a = sys.argv
if 0:
    a = ("main.py 264933697 " + str(input("args: "))).split(" ")
if len(a) < 4:
    sys.exit()

uid = a[1]
u = User(uid)
t = Tree(j("map.json"), u)
markup = Process(None, t, u).markup()
msg = u.last_message
a = a[2:]
l = [i.lower() for i in a]
op = l[0]
db = Database().connect("data.db")

def sm(msg, mu = True):
    if mu:
        bot.send_message(uid, msg, reply_markup=markup)
    else:
        bot.send_message(uid, msg)

def main():
    global markup
    result = None
    if op[0] == "g":  # e.g. python3 main.py [ID] g[d] <col_name|data_key>
        if len(op) == 2 and op[1] == "d":
            result = u.gd(a[1])
        else:
            result = u.g(a[1])
    elif op[0] == "s":  # e.g. python3 main.py [ID] s[d] <col_name|data_key> <value>
        val = " ".join(a[2:])
        if len(op) == 2 and op[1] == "d":
            result = u.sd(a[1], val)
        else:
            result = u.s(a[1], val)
    elif op == "q":  # e.g. python3 main.py [ID] q select * from users
        bot.send_message(uid, str(db.execute(" ".join(a[1:]))))
        #pass
    # e.g. python3 main.py [ID] e userlastseen / set result to show in output
    elif op == "e":
        if a[1] == "profile":
            puid = db.execute("select user_id from users where user_id != ? and data like '%\"status_up\"%' ORDER BY RANDOM() LIMIT 1",(uid, ))[0]["user_id"]
            ru = User(puid)
            ud = ru.gd()
            cap = "%s, %s, %s\n%s" % (ud["name"], ru.g("age"), ud["city"], ud["description"])
            bot.send_photo(uid, photo = ud["photo"] , caption = cap,reply_markup=markup)
        elif a[1] == "self":
            ud = u.gd()
            cap = "%s, %s, %s\n%s" % (ud["name"], u.g("age"), ud["city"], ud["description"])
            bot.send_photo(uid, photo = ud["photo"] , caption = cap,reply_markup=markup)
        elif a[1] == "like":
            bot.send_message(uid, "salam")
        elif a[1] == "editprofselect":
            pth = ""
            m = msg["text"]
            if m == "name":
                pth = "name"
            elif m == "age":
                pth = "age"
            elif m == "city":
                pth = "city"
            elif m == "photo":
                pth = "photo"
            elif m == "description":
                pth = "desc"
            elif m[0] == "r":
                pth = "gender"
            elif m == "demo":
                pth = "demo"
            elif m == "back":
                t.next("back")
                pth = "back"
            t.next(pth)
            newnode_callback(t)
            markup = Process(None, t, u).markup()
            sm(t.process(msg).output(), 1)
    return result
print(main())
