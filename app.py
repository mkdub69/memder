import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, session
import dropbox
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "devsecret")  # Für Sessions

# Dropbox-Zugang (Token aus Umgebungsvariable)
DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")
dbx = dropbox.Dropbox(DROPBOX_TOKEN)
DROPBOX_FOLDER = "/memder"

# SQLite-Datei
DB_FILE = "votes.db"

# DB initialisieren
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS votes (image1 TEXT, image2 TEXT, winner TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS flags (image TEXT UNIQUE)")
        conn.commit()

# Liste gültiger Memes (nicht geflaggt)
def get_valid_memes():
    flagged = set(row[0] for row in sqlite3.connect(DB_FILE).execute("SELECT image FROM flags"))
    entries = dbx.files_list_folder(DROPBOX_FOLDER).entries
    files = [f.path_lower for f in entries if isinstance(f, dropbox.files.FileMetadata)]
    return [f for f in files if f not in flagged]

def get_two_random_memes():
    valid_memes = get_valid_memes()
    if len(valid_memes) < 2:
        return None, None
    return random.sample(valid_memes, 2)

# Login-Seite
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "6969":
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Falsches Passwort.")
    return render_template("login.html")

# Startseite – nur bei Login
@app.route("/")
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    meme1, meme2 = get_two_random_memes()
    if not meme1 or not meme2:
        return "Nicht genug valide Memes vorhanden."
    return render_template("index.html", meme1=meme1, meme2=meme2)

# Abstimmen oder Flaggen
@app.route("/vote", methods=["POST"])
def vote():
    selected = request.form.get("selected_image")
    action = request.form.get("action")
    meme1 = request.form.get("meme1")
    meme2 = request.form.get("meme2")

    if action == "vote" and selected in [meme1, meme2]:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO votes (image1, image2, winner) VALUES (?, ?, ?)", (meme1, meme2, selected))
            conn.commit()
    elif action == "flag" and selected in [meme1, meme2]:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR IGNORE INTO flags (image) VALUES (?)", (selected,))
            conn.commit()

    return redirect(url_for("index"))

# Bilder vom Dropbox-Server abrufen
@app.route("/image")
def serve_image():
    path = request.args.get("path")
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

# Start
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=10000)
