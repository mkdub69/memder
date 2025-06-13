import os
import random
import sqlite3
from flask import Flask, request, redirect, render_template, send_file
import dropbox
from io import BytesIO

app = Flask(__name__)

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER = "/memder"
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS votes (path TEXT PRIMARY KEY, count INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS flags (path TEXT PRIMARY KEY)")
conn.commit()

def list_memes():
    entries = dbx.files_list_folder(DROPBOX_FOLDER).entries
    c.execute("SELECT path FROM flags")
    flagged = {row[0] for row in c.fetchall()}
    return [e.path_display for e in entries if isinstance(e, dropbox.files.FileMetadata) and e.path_display not in flagged]

@app.route("/")
def index():
    memes = list_memes()
    if len(memes) < 2:
        return "Nicht genug Memes verfügbar."
    meme1, meme2 = random.sample(memes, 2)
    return render_template("index.html", meme1=meme1, meme2=meme2)

@app.route("/vote", methods=["POST"])
def vote():
    selected = request.form["selected"]
    action = request.form["action"]
    if action == "vote":
        c.execute("INSERT INTO votes (path, count) VALUES (?, 1) ON CONFLICT(path) DO UPDATE SET count = count + 1", (selected,))
    elif action == "flag":
        c.execute("INSERT OR IGNORE INTO flags (path) VALUES (?)", (selected,))
    conn.commit()
    return redirect("/")

@app.route("/leaderboard")
def leaderboard():
    c.execute("SELECT path, count FROM votes ORDER BY count DESC LIMIT 10")
    results = c.fetchall()
    return render_template("leaderboard.html", results=results)

@app.route("/image")
def image():
    path = request.args.get("path")
    _, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(debug=True)
