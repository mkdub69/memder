import os
import random
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, send_file
import dropbox
from io import BytesIO

# Konfiguration
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"

app = Flask(__name__)
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# SQLite-Datenbank einrichten
conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        path TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS flags (
        path TEXT PRIMARY KEY
    )
''')
conn.commit()

def list_images():
    entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
    images = [entry.path_display for entry in entries if isinstance(entry, dropbox.files.FileMetadata)]
    
    # Geﬂaggte Bilder ausschließen
    c.execute("SELECT path FROM flags")
    flagged = set(row[0] for row in c.fetchall())
    return [img for img in images if img not in flagged]

def get_random_images():
    images = list_images()
    if len(images) < 2:
        return images
    return random.sample(images, 2)

@app.route("/")
def index():
    images = get_random_images()
    if len(images) < 2:
        return "<h1>Keine weiteren Memes verfügbar.</h1>"

    return render_template_string(TEMPLATE, img1=images[0], img2=images[1])

@app.route("/vote", methods=["POST"])
def vote():
    selected = request.form["selected"]
    action = request.form["action"]

    if action == "vote":
        c.execute("INSERT INTO votes (path, count) VALUES (?, 1) ON CONFLICT(path) DO UPDATE SET count = count + 1", (selected,))
        conn.commit()
    elif action == "flag":
        c.execute("INSERT OR IGNORE INTO flags (path) VALUES (?)", (selected,))
        conn.commit()

    return redirect(url_for("index"))

@app.route("/leaderboard")
def leaderboard():
    c.execute("SELECT path, count FROM votes ORDER BY count DESC LIMIT 10")
    top = c.fetchall()
    return render_template_string(LEADERBOARD_TEMPLATE, top=top)

@app.route("/image")
def image():
    path = request.args.get("path")
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype='image/jpeg')

# HTML Templates
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>memder</title>
    <style>
        body {
            font-family: 'Comic Sans MS', cursive, sans-serif;
            text-align: center;
            background: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        .meme-container {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 20px;
        }
        .meme {
            border: 5px solid transparent;
            padding: 5px;
        }
        .meme.selected {
            border-color: green;
        }
        .buttons {
            margin-top: 20px;
        }
        button {
            font-size: 20px;
            padding: 10px 30px;
            margin: 10px;
        }
        footer {
            font-size: 12px;
            color: #777;
            margin-top: 30px;
        }
    </style>
    <script>
        let selected = null;
        function selectMeme(id, path) {
            selected = path;
            document.getElementById("meme1").classList.remove("selected");
            document.getElementById("meme2").classList.remove("selected");
            document.getElementById(id).classList.add("selected");
            document.getElementById("selectedInput").value = path;
        }

        function submitVote(action) {
            if (!selected) {
                alert("Bitte zuerst ein Meme auswählen.");
                return;
            }
            document.getElementById("actionInput").value = action;
            document.getElementById("voteForm").submit();
        }
    </script>
</head>
<body>
    <h2 style="font-size: 18px;">Welches Meme ist geiler?</h2>
    <div class="meme-container">
        <div class="meme" id="meme1" onclick="selectMeme('meme1', '{{ img1 }}')">
            <img src="/image?path={{ img1 }}" width="100%">
        </div>
        <div class="meme" id="meme2" onclick="selectMeme('meme2', '{{ img2 }}')">
            <img src="/image?path={{ img2 }}" width="100%">
        </div>
    </div>
    <form method="POST" action="/vote" id="voteForm">
        <input type="hidden" name="selected" id="selectedInput">
        <input type="hidden" name="action" id="actionInput">
        <div class="buttons">
            <button type="button" style="background: lightgreen;" onclick="submitVote('vote')">Abstimmen</button>
            <button type="button" style="background: salmon;" onclick="submitVote('flag')">Melden</button>
        </div>
    </form>
    <a href="/leaderboard">Top Memes ansehen</a>
    <footer>Zeitraum: Januar – Juni 2010</footer>
</body>
</html>
"""

LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Top Memes</title>
    <style>
        body {
            font-family: 'Comic Sans MS', cursive, sans-serif;
            text-align: center;
            margin: 20px;
        }
        .meme {
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <h1>Top Memes</h1>
    {% for path, count in top %}
        <div class="meme">
            <img src="/image?path={{ path }}" width="80%">
            <p>Votes: {{ count }}</p>
        </div>
    {% endfor %}
    <footer>Zeitraum: Januar – Juni 2010</footer>
</body>
</html>
"""
