import os
import random
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, send_file
import dropbox
from io import BytesIO

# Konfiguration
DROPBOX_ACCESS_TOKEN = os.environ.get('DROPBOX_ACCESS_TOKEN')
DROPBOX_FOLDER_PATH = "/memder"

app = Flask(__name__)
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# SQLite DB vorbereiten
def init_db():
    conn = sqlite3.connect("votes.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        meme TEXT,
        votes INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS flagged (
        meme TEXT PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

# Nur ungemeldete Bilder abrufen
def list_memes():
    result = dbx.files_list_folder(DROPBOX_FOLDER_PATH)
    all_files = [entry.path_display for entry in result.entries if isinstance(entry, dropbox.files.FileMetadata)]
    flagged = get_flagged()
    return [f for f in all_files if f not in flagged]

def get_flagged():
    conn = sqlite3.connect("votes.db")
    c = conn.cursor()
    c.execute("SELECT meme FROM flagged")
    flagged = [row[0] for row in c.fetchall()]
    conn.close()
    return flagged

# Zwei zufällige Memes auswählen
def get_two_memes():
    memes = list_memes()
    if len(memes) < 2:
        return None, None
    return random.sample(memes, 2)

@app.route("/")
def index():
    meme1, meme2 = get_two_memes()
    if not meme1 or not meme2:
        return "Zu wenige Memes verfügbar."
    return render_template_string(TEMPLATE, meme1=meme1, meme2=meme2)

@app.route("/vote", methods=["POST"])
def vote():
    voted_meme = request.form["meme"]
    conn = sqlite3.connect("votes.db")
    c = conn.cursor()
    c.execute("INSERT INTO votes (meme, votes) VALUES (?, 1) ON CONFLICT(meme) DO UPDATE SET votes = votes + 1", (voted_meme,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/flag", methods=["POST"])
def flag():
    flagged_meme = request.form["meme"]
    conn = sqlite3.connect("votes.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO flagged (meme) VALUES (?)", (flagged_meme,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/leaderboard")
def leaderboard():
    conn = sqlite3.connect("votes.db")
    c = conn.cursor()
    c.execute("SELECT meme, votes FROM votes ORDER BY votes DESC LIMIT 10")
    results = c.fetchall()
    conn.close()
    return render_template_string(LEADERBOARD_TEMPLATE, leaderboard=results)

@app.route("/image")
def image():
    path = request.args.get("path")
    _, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

# HTML Templates
TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Memder</title>
    <style>
        body { font-family: Comic Sans MS, cursive; text-align: center; margin: 10px; }
        img { max-width: 90%%; border: 3px solid #333; margin: 5px; }
        form { display: inline-block; margin: 10px; }
        .small { font-size: 12px; margin-top: 20px; color: #666; }
    </style>
</head>
<body>
    <h3>Welches Meme ist geiler?</h3>

    <div>
        <form action="/vote" method="post">
            <input type="hidden" name="meme" value="{{ meme1 }}">
            <button type="submit"><img src="/image?path={{ meme1 }}"></button>
        </form>
        <form action="/flag" method="post">
            <input type="hidden" name="meme" value="{{ meme1 }}">
            <button type="submit">🚩 melden</button>
        </form>
    </div>

    <div>
        <form action="/vote" method="post">
            <input type="hidden" name="meme" value="{{ meme2 }}">
            <button type="submit"><img src="/image?path={{ meme2 }}"></button>
        </form>
        <form action="/flag" method="post">
            <input type="hidden" name="meme" value="{{ meme2 }}">
            <button type="submit">🚩 melden</button>
        </form>
    </div>

    <br>
    <a href="/leaderboard">Top 10 Memes anzeigen</a>
    <div class="small">Memes aus Januar – Juni 2010</div>
</body>
</html>
"""

LEADERBOARD_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Top Memes</title>
    <style>
        body { font-family: Comic Sans MS, cursive; text-align: center; margin: 10px; }
        img { max-width: 90%%; border: 3px solid #333; margin: 10px auto; display: block; }
        .small { font-size: 12px; margin-top: 20px; color: #666; }
    </style>
</head>
<body>
    <h3>Top 10 Memes</h3>
    {% for meme, votes in leaderboard %}
        <img src="/image?path={{ meme }}">
        <div>{{ votes }} Votes</div>
    {% endfor %}
    <div class="small">Memes aus Januar – Juni 2010</div>
</body>
</html>
"""

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
