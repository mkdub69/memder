import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file
import dropbox
from io import BytesIO

# Dropbox-Konfiguration
DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"
dbx = dropbox.Dropbox(DROPBOX_TOKEN)

# Flask-App
app = Flask(__name__)

# Datenbank initialisieren
def init_db():
    with sqlite3.connect("votes.db") as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                image TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS flagged (
                image TEXT PRIMARY KEY
            )
        ''')
        conn.commit()

init_db()

# Bilder aus Dropbox abrufen (nur nicht-geflaggte)
def list_images():
    entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
    with sqlite3.connect("votes.db") as conn:
        c = conn.cursor()
        c.execute("SELECT image FROM flagged")
        flagged = {row[0] for row in c.fetchall()}
    images = [e.path_lower for e in entries if isinstance(e, dropbox.files.FileMetadata) and e.path_lower not in flagged]
    return images

# Hauptseite
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected = request.form["action"]
        if selected.startswith("/"):
            if "vote" in request.form["action"]:
                with sqlite3.connect("votes.db") as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO votes (image, count) VALUES (?, 1) ON CONFLICT(image) DO UPDATE SET count = count + 1", (selected,))
                    conn.commit()
            elif "flag" in request.form["action"]:
                with sqlite3.connect("votes.db") as conn:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO flagged (image) VALUES (?)", (selected,))
                    conn.commit()
        return redirect(url_for("index"))

    images = list_images()
    if len(images) < 2:
        return "Nicht genügend ungeflaggte Memes verfügbar."
    img1, img2 = random.sample(images, 2)
    return render_template("index.html", img1=img1, img2=img2)

# Bild aus Dropbox anzeigen
@app.route("/image")
def get_image():
    path = request.args.get("path")
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

# Bestenliste
@app.route("/leaderboard")
def leaderboard():
    with sqlite3.connect("votes.db") as conn:
        c = conn.cursor()
        c.execute("SELECT image, count FROM votes ORDER BY count DESC LIMIT 10")
        top_images = c.fetchall()
    return render_template("leaderboard.html", images=top_images)
