import os
import random
import sqlite3
from flask import Flask, render_template_string, request, redirect, send_file, session
import dropbox
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"

# Initialisiere Dropbox
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# Datenbank initialisieren
conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        image TEXT,
        count INTEGER DEFAULT 0
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS flagged (
        image TEXT PRIMARY KEY
    )
''')
conn.commit()

# Templates
TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Welches Meme ist geiler?</title>
    <style>
        body { font-family: "Comic Sans MS", cursive, sans-serif; text-align: center; }
        .meme-container { display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; margin-top: 20px; }
        .meme { border: 2px solid black; padding: 10px; }
        .meme img { max-width: 100%; height: auto; }
        .footer { font-size: 0.8em; margin-top: 30px; color: #666; }
    </style>
</head>
<body>
    {% if not session.get("authenticated") %}
        <h2>Passwort erforderlich</h2>
        <form method="post" action="/login">
            <input type="password" name="password" />
            <input type="submit" value="Einloggen" />
        </form>
    {% else %}
        <h2 style="font-size: 1.5em;">Welches Meme ist geiler?</h2>
        <div class="meme-container">
            {% for path in images %}
            <div class="meme">
                <img src="/image?path={{ path }}" alt="Meme" /><br>
                <form method="post" action="/vote">
                    <input type="hidden" name="vote" value="{{ path }}">
                    <button type="submit">Wählen</button>
                </form>
                <form method="post" action="/flag" style="margin-top: 5px;">
                    <input type="hidden" name="flag" value="{{ path }}">
                    <button type="submit">Melden</button>
                </form>
            </div>
            {% endfor %}
        </div>
        <p><a href="/leaderboard">Top Memes anzeigen</a></p>
        <div class="footer">Bewertete Monate: Januar – Juni 2010</div>
    {% endif %}
</body>
</html>
'''

LEADERBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Top Memes</title>
    <style>
        body { font-family: "Comic Sans MS", cursive, sans-serif; text-align: center; }
        img { max-width: 90%%; margin: 10px auto; display: block; border: 2px solid black; }
        .footer { font-size: 0.8em; margin-top: 30px; color: #666; }
    </style>
</head>
<body>
    <h2>Top Memes</h2>
    {% for path in images %}
        <img src="/image?path={{ path }}" alt="Meme">
    {% endfor %}
    <p><a href="/">Zurück zur Bewertung</a></p>
    <div class="footer">Bewertete Monate: Januar – Juni 2010</div>
</body>
</html>
'''

# Funktionen
def list_images():
    try:
        flagged = {row[0] for row in c.execute("SELECT image FROM flagged")}
        entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH, recursive=True).entries
        images = [entry.path_display for entry in entries if isinstance(entry, dropbox.files.FileMetadata)]
        images = [img for img in images if img not in flagged]
        return images
    except Exception as e:
        print("Fehler beim Laden der Bilder:", e)
        return []

@app.route("/", methods=["GET"])
def index():
    if not session.get("authenticated"):
        return render_template_string(TEMPLATE, images=[], session=session)
    images = list_images()
    if len(images) < 2:
        return "<h2>Zu wenig ungemeldete Memes übrig :(</h2>"
    return render_template_string(TEMPLATE, images=random.sample(images, 2), session=session)

@app.route("/vote", methods=["POST"])
def vote():
    image = request.form["vote"]
    c.execute("INSERT INTO votes (image, count) VALUES (?, 1) ON CONFLICT(image) DO UPDATE SET count = count + 1", (image,))
    conn.commit()
    return redirect("/")

@app.route("/flag", methods=["POST"])
def flag():
    image = request.form["flag"]
    c.execute("INSERT OR IGNORE INTO flagged (image) VALUES (?)", (image,))
    conn.commit()
    return redirect("/")

@app.route("/image")
def image():
    path = request.args.get("path")
    _, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

@app.route("/leaderboard")
def leaderboard():
    rows = c.execute("SELECT image FROM votes WHERE image NOT IN (SELECT image FROM flagged) ORDER BY count DESC LIMIT 10").fetchall()
    images = [row[0] for row in rows]
    return render_template_string(LEADERBOARD_TEMPLATE, images=images)

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("password") == "6969":
        session["authenticated"] = True
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
