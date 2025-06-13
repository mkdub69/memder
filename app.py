import os
import random
import sqlite3
from flask import Flask, render_template_string, request, redirect, send_file
import dropbox
from io import BytesIO

app = Flask(__name__)

DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"
PASSWORD = "6969"

dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# SQLite initialisieren
conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        meme TEXT,
        count INTEGER
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS flagged (
        meme TEXT PRIMARY KEY
    )
''')
conn.commit()

# Bilder aus Dropbox holen
def list_images():
    entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
    return [entry.path_display for entry in entries if isinstance(entry, dropbox.files.FileMetadata)]

# Zwei zufällige, nicht-geflaggte Bilder auswählen
def get_two_random_images():
    images = [img for img in list_images() if not is_flagged(img)]
    if len(images) < 2:
        return None, None
    return random.sample(images, 2)

# Bild flaggen
def flag_image(path):
    c.execute("INSERT OR IGNORE INTO flagged (meme) VALUES (?)", (path,))
    conn.commit()

def is_flagged(path):
    c.execute("SELECT 1 FROM flagged WHERE meme = ?", (path,))
    return c.fetchone() is not None

# Votings speichern
def vote_for(image_path):
    c.execute("INSERT INTO votes (meme, count) VALUES (?, 1) ON CONFLICT(meme) DO UPDATE SET count = count + 1", (image_path,))
    conn.commit()

# Top-Votings holen
def get_top_voted(limit=10):
    c.execute("SELECT meme, count FROM votes ORDER BY count DESC LIMIT ?", (limit,))
    return c.fetchall()

# Bild von Dropbox serven
@app.route("/image")
def serve_image():
    path = request.args.get("path")
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

# Passwort-Check
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST" and request.form.get("pw") != PASSWORD:
        return render_template_string('<p>Falsches Passwort. <a href="/">Zurück</a></p>')
    if request.method == "POST":
        return redirect("/vote")

    return render_template_string('''
        <form method="POST" style="text-align:center; font-family: Comic Sans MS;">
            <h3>🔒 Passwort bitte:</h3>
            <input type="password" name="pw">
            <button type="submit">Los geht's</button>
        </form>
    ''')

# Haupt-Votingseite
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        if "winner" in request.form:
            vote_for(request.form["winner"])
        elif "flag1" in request.form:
            flag_image(request.form["flag1"])
        elif "flag2" in request.form:
            flag_image(request.form["flag2"])
        return redirect("/vote")

    img1, img2 = get_two_random_images()
    if not img1 or not img2:
        return "<p>Zu wenig ungemeldete Memes übrig.</p>"

    return render_template_string('''
        <html>
        <head>
            <title>Welches Meme ist geiler?</title>
            <style>
                body { font-family: "Comic Sans MS"; text-align: center; }
                img { width: 90%%; max-width: 300px; margin: 10px; border: 4px solid black; }
                .meme-container { display: flex; flex-direction: column; align-items: center; gap: 10px; }
                form { display: flex; flex-direction: column; align-items: center; gap: 10px; }
                .row { display: flex; justify-content: space-around; flex-wrap: wrap; }
            </style>
        </head>
        <body>
            <h3>Welches Meme ist geiler?</h3>
            <form method="POST">
                <div class="row">
                    <div class="meme-container">
                        <button type="submit" name="winner" value="{{ img1 }}">😂</button>
                        <img src="/image?path={{ img1 }}" alt="Meme 1">
                        <button type="submit" name="flag1" value="{{ img1 }}">🛑 Melden</button>
                    </div>
                    <div class="meme-container">
                        <button type="submit" name="winner" value="{{ img2 }}">😂</button>
                        <img src="/image?path={{ img2 }}" alt="Meme 2">
                        <button type="submit" name="flag2" value="{{ img2 }}">🛑 Melden</button>
                    </div>
                </div>
            </form>
            <a href="/leaderboard">🏆 Zur Bestenliste</a>
            <p style="font-size: small; margin-top: 20px;">Zeitraum: Januar – Juni 2010</p>
        </body>
        </html>
    ''', img1=img1, img2=img2)

# Bestenliste anzeigen
@app.route("/leaderboard")
def leaderboard():
    top_memes = get_top_voted()
    return render_template_string('''
        <html>
        <head>
            <title>Top Memes</title>
            <style>
                body { font-family: "Comic Sans MS"; text-align: center; }
                img { width: 90%%; max-width: 300px; margin: 10px; border: 4px solid black; }
            </style>
        </head>
        <body>
            <h2>🏆 Die 10 geilsten Memes</h2>
            {% for meme, count in memes %}
                <div>
                    <img src="/image?path={{ meme }}" alt="Top Meme">
                    <p>Votes: {{ count }}</p>
                </div>
            {% endfor %}
            <a href="/vote">🔙 Zurück zum Voting</a>
            <p style="font-size: small; margin-top: 20px;">Zeitraum: Januar – Juni 2010</p>
        </body>
        </html>
    ''', memes=top_memes)

if __name__ == "__main__":
    app.run(debug=True)
