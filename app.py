import os
import random
import sqlite3
from flask import Flask, request, redirect, url_for, send_file, render_template
import dropbox
from io import BytesIO

app = Flask(__name__)

# Dropbox-Konfiguration über Umgebungsvariable (Render)
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# SQLite-Datenbank vorbereiten
conn = sqlite3.connect('votes.db', check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT UNIQUE,
    vote_count INTEGER DEFAULT 0,
    flagged INTEGER DEFAULT 0
)
""")
conn.commit()

def is_flagged(path):
    c.execute("SELECT flagged FROM votes WHERE image_path = ?", (path,))
    result = c.fetchone()
    return result and result[0] == 1

def list_images():
    try:
        entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
        return [e.path_display for e in entries
                if isinstance(e, dropbox.files.FileMetadata)
                and not is_flagged(e.path_display)]
    except Exception as e:
        print("Fehler beim Laden der Bilder:", e)
        return []

@app.route("/")
def index():
    images = list_images()
    if len(images) < 2:
        return "Nicht genug Memes zum Anzeigen"
    img1, img2 = random.sample(images, 2)
    return render_template("index.html", img1=img1, img2=img2)

@app.route("/vote", methods=["POST"])
def vote():
    selected_image = request.form["selected_image"]
    action = request.form["action"]

    if action == "vote":
        c.execute("INSERT OR IGNORE INTO votes (image_path, vote_count, flagged) VALUES (?, 0, 0)", (selected_image,))
        c.execute("UPDATE votes SET vote_count = vote_count + 1 WHERE image_path = ?", (selected_image,))
    elif action == "flag":
        c.execute("INSERT OR IGNORE INTO votes (image_path, vote_count, flagged) VALUES (?, 0, 0)", (selected_image,))
        c.execute("UPDATE votes SET flagged = 1 WHERE image_path = ?", (selected_image,))
    
    conn.commit()
    return redirect(url_for("index"))

@app.route("/image")
def image():
    path = request.args.get("path")
    _, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype="image/jpeg")

@app.route("/leaderboard")
def leaderboard():
    c.execute("SELECT image_path, vote_count FROM votes WHERE flagged = 0 ORDER BY vote_count DESC LIMIT 50")
    images = c.fetchall()
    return render_template("leaderboard.html", images=images)

if __name__ == "__main__":
    app.run(debug=True)
