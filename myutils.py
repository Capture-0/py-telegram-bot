# users table: CREATE TABLE users (user_id TEXT UNIQUE,age INTEGER,gender TEXT,coordinate TEXT,created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,tree TEXT,ptree TEXT,last_message TEXT,data TEXT)
import subprocess
import requests
import telebot
import sqlite3
import random
import json
import re

TOKEN = "253284677:AAGH-nxJuBFmuHWY8RL4E49pHgP-pvWpUkI"
bot = telebot.TeleBot(TOKEN)
DATABASE = "data.db"

class Database:
    connectionString = None
    dry = False

    def __init__(self, dry=False):
        self.dry = dry

    def connect(self, db):
        self.connectionString = db
        return self

    def execute(self, qry, vals=None):
        if self.dry:
            return
        connection = sqlite3.connect(self.connectionString)
        crsr = connection.cursor()
        if vals == None:
            crsr.execute(qry)
        else:
            crsr.execute(qry, vals)
        res = ""
        if qry[:6].lower() != "select":
            connection.commit()
        if qry[:6].lower() == "select":
            res = [dict(zip(['user_id', 'age', 'gender', 'coordinate',
                        'created', 'tree', 'ptree', 'last_message', 'data'], i)) for i in crsr.fetchall()]
        elif qry[:6].lower() == "insert":
            res = crsr.lastrowid
        else:
            res = connection.total_changes
        crsr.close()
        connection.close()
        return res

    def user_data(self, user_id):
        return self.execute("select * from users where user_id = ?", (user_id,))[0]

class User:
    id = None
    db = Database().connect(DATABASE)

    def __init__(self, id):
        if len(self.db.execute("select * from users where user_id = " + str(id))) == 0:
            raise
        self.id = id

    @property
    def last_message(self):
        lm = self.db.user_data(self.id)["last_message"]
        if lm == None or lm == "":
            self.db.execute(
                "update users set last_message = '{}' where user_id = ?", (self.id,))
        lm = self.db.user_data(self.id)["last_message"]
        return json.loads(lm)

    @last_message.setter
    def last_message(self, value):
        u = User(self.id)
        u.s("last_message", value)

    def g(self, key):
        return self.db.execute("select * from users where user_id = ?", (self.id,))[0][key]

    def s(self, key, value):
        return self.db.execute("update users set %s = ? where user_id = ?" % key, (value, self.id))

    def gd(self, key=None):
        ud = self.db.user_data(self.id)["data"]
        if ud == None or ud == "":
            self.db.execute(
                "update users set data = '{}' where user_id = ?", (self.id,))
        ud = self.db.user_data(self.id)["data"]
        if key == None:
            return json.loads(ud)
        return (None if key not in json.loads(ud) else json.loads(ud)[key])

    def sd(self, key, value):
        j = self.gd()
        if j == None:
            j = {key: value}
        j[key] = value
        self.db.execute(
            "update users set data = ? where user_id = ?", (json.dumps(j), self.id))

    def send_message(self, msg, markup=None):
        if msg == None:
            return
        if markup == None:
            bot.send_message(self.id, msg)
        else:
            bot.send_message(self.id, msg, reply_markup=markup)


class Process:
    value, tree, user = None, None, None

    def __init__(self, value, tree, user):
        self.value = value
        self.tree = tree
        self.user = user

    def input(self):  # this function checks if the input is correct returns the next level node name else returns None
        n = self.tree.current
        msg = self.value
        msg_text = msg.text
        if "expect" in n:
            ex = n["expect"]
            tp = ex["type"].lower()
            op = ex["op"].replace("[MSG]", msg_text)
            r = None
            if tp == "text":
                if "pattern" in ex and not m(ex["pattern"], msg_text):
                    return None
                if "markup" in ex:
                    for i in ex["markup"]:
                        if msg_text == i["title"]:
                            self.command(i["op"])
                            return self.next(False)
                r = n["next"]["name"]
            elif tp == "markup":
                if self.in_markup(msg_text):
                    r = self.next()
            elif tp == "photo":
                if msg.photo:
                    op = op.replace("[PHOTO]", msg.photo[0].file_id)
                    r = n["next"]["name"]
            self.command(op)
            return r
        else:
            return self.next()

    def next(self, check_markup=True):
        n = self.tree.current
        if "markup" in n and type(n["next"]) == list and check_markup:
            m = n["markup"]
            a = []
            for i in m:
                if type(i) == str:
                    a.append(i)
                else:
                    a += [j for j in i]
            for i in a:
                if self.value.text == i["title"]:
                    if "if" not in i or self.command(i["if"]) == "1":
                        return i["next"]
        elif type(n["next"]) == str:
            return "@" + n["next"]
        elif type(n["next"]) == dict:
            return n["next"]["name"]
        return None

    def output(self):  # this function returns what should be shown to user
        if "say" not in self.tree.current:
            return None
        o = self.tree.current["say"]
        if type(o) == str:
            if o[0] == "/":
                self.command(o[1:])
                return None
            else:
                return o
        elif type(o) == dict:
            return parse_fstr(o, self)
        return None

    def markup(self):
        n = self.tree.current
        ma = []
        if "markup" in n:
            m = n["markup"]
            if type(m) == list:  # if makrup is an array
                if type(n["next"]) != list:
                    ma = m
                else:  # parse array of objects
                    for i in m:
                        if type(i) == list:
                            ma.append([j["title"] for j in i])
                        elif type(i) == dict:
                            ma.append(i["title"])
                        else:
                            raise Exception(
                                "all elements in the array must be object or array of objects")
            else:  # if makrup is a string
                if m == "col":
                    ma = [[i["name"] for i in n["next"]]]
                elif m == "row":
                    ma = [i["name"] for i in n["next"]]
                else:
                    ma = json.loads(self.command("m %s" % m))["list"]
        else:
            ma = None
        return ma

    def in_markup(self, title):
        m = []
        for i in self.markup():
            if type(i) == str:
                m.append(i)
            else:
                m += [j for j in i]
        return title in m

    def command(self, cmd, uid=None):
        id = uid
        if id == None:
            id = str(self.user.id)
        r = "python3 main.py " + id + " " + cmd
        return subprocess.Popen(r.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8')


class Tree:
    tree, current, user, p = None, None, None, None

    def __init__(self, json, user):
        self.tree = json
        self.user = user
        if self.user.g("tree") == None:
            self.user.s("tree", self.tree["name"])
        self.route(self.user.g("tree"))

    @property
    def path(self):
        r = self.user.g("tree")
        if r == None or r == "":
            self.user.s("tree", self.tree["name"])
        return self.user.g("tree")

    @path.setter
    def path(self, value):
        c = self.user.g("tree")
        if c != None and c != "":
            self.user.s("ptree", c)
        self.user.s("tree", value)

    def next(self, name=None, title=None):
        r = True
        if type(self.current["next"]) == dict:
            self.current = self.current["next"]
        elif (name or title) and not (name and title) and type(self.current["next"]) == list:
            for i in range(len(self.current["next"])):
                if self.current["next"][i]["name"] == name or self.current["next"][i]["title"] == title:
                    self.current = self.current["next"][i]
                    break
        elif type(self.current["next"]) == str:
            a = self.current["next"]
            self.current = self.tree
            self.route(a)
            r = False
        else:
            r = False
        if r:
            self.path += "/%s" % self.current["name"]
            return self.current
        else:
            return None

    def route(self, path):
        src = {"node": self.current, "path": self.path}
        self.current = self.tree
        self.path = self.tree["name"]
        if path == self.tree["name"]:
            self.current = self.tree
            return
        for i in path.split('/')[1:]:
            if self.next(i) == None:
                break
        if "meta" in self.current and "if" in self.current["meta"] and Process(None, self, self.user).command(self.current["meta"]["if"], self.user.id) != "1":
            self.current = src["node"]
            self.path = src["path"]

    def process(self, value=None):
        if self.user:
            if self.p == None:
                self.p = Process(value, self, self.user)
            else:
                self.p.value = value
            return self.p
        else:
            return None

def command(cmd, uid):
    r = "python3 main.py " + str(uid) + " " + cmd
    return subprocess.Popen(r.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode('utf-8')

def parse_fstr(obj, update):
    if "fstr" in obj and "args" in obj:
        res = obj["fstr"]
        for i in range(len(obj["args"])):
            cmd = obj["args"][i].replace("[ID]", str(update.chat.id)).replace(
                "[MSG]", str(update.text))
            res = res.replace("$%s" % i, command(
                obj["args"][i], update.chat.id))
        return res
    else:
        return None

def newnode_callback(tree):
    if "meta" in tree.current:
        if "execute" in tree.current["meta"]:
            e = tree.current["meta"]["execute"]
            if type(e) == str:
                command(e, tree.user.id)
            else:
                for i in e:
                    command(i, tree.user.id)

def download(url, name):
    r = requests.get(url, allow_redirects=True)
    f = open(name, 'wb')
    f.write(r.content)
    f.close()

def tgdownload(file_id):
    gf = bot.get_file(file_id)
    download("https://api.telegram.org/file/bot%s/%s" %
             (TOKEN, gf.file_path), 'testfile')
    return gf

def get_markup_by_array(val):
    if type(val) == list:
        markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True)
        for i in val:
            if type(i) == list:
                markup.row(*(i))
            else:
                markup.row(i)
        return markup
    return None

def parse_fstr(obj, process):
    if "fstr" in obj and "args" in obj:
        args = obj["args"]
        res = obj["fstr"]
        for i in range(len(args)):
            executed = process.command(args[i], process.user.id)
            res = res.replace("$%s" % i, executed)
        return res
    else:
        return None

def m(pattern, inp, insensitive=False):
    if insensitive:
        return re.findall(pattern, inp, re.I)
    return re.findall(pattern, inp)

def randstr(l=16, chars="abcdef0123456789"):
    return ''.join(random.choices(chars, k=l))

def j(p):
    f = open(p, "r")
    r = f.read()
    f.close()
    return json.loads(r)
