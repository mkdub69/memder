import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import dropbox

app = Flask(__name__)

# Dropbox-Zugang
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# Datenbank vorbereiten
conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    winner TEXT,
    loser TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS flagged (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image TEXT
)
""")
conn.commit()

# Lade Bilder von Dropbox
def get_all_images():
    folders = ["/memes/jan", "/memes/feb", "/memes/mar", "/memes/apr", "/memes/mai", "/memes/jun"]
    files = []
    for folder in folders:
        try:
            res = dbx.files_list_folder(folder)
            for entry in res.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    files.append(entry.path_lower)
        except Exception:
            pass
    return files

# Generiere zufälliges Bildpaar (gefiltert)
def get_random_image_pair():
    images = get_all_images()
    c.execute("SELECT image FROM flagged")
    flagged_images = [row[0] for row in c.fetchall()]
    valid_images = [img for img in images if img not in flagged_images]
    if len(valid_images) < 2:
        return None, None
    return random.sample(valid_images, 2)

# Direktlink zu Dropbox-Dateien (Content URLs)
def get_image_link(path):
    link = dbx.files_get_temporary_link(path).link
    return link

@app.route("/", methods=["GET"])
def index():
    img1_path, img2_path = get_random_image_pair()
    if not img1_path or not img2_path:
        return "Nicht genug valide Memes vorhanden."
    img1_url = get_image_link(img1_path)
    img2_url = get_image_link(img2_path)
    return render_template("index.html", img1_url=img1_url, img2_url=img2_url,
                           img1_path=img1_path, img2_path=img2_path)

@app.route("/vote", methods=["POST"])
def vote():
    selected = request.form.get("selected")
    action = request.form.get("action")
    img1 = request.form.get("img1")
    img2 = request.form.get("img2")

    if action == "vote" and selected:
        winner = selected
        loser = img2 if selected == img1 else img1
        c.execute("INSERT INTO votes (winner, loser) VALUES (?, ?)", (winner, loser))
        conn.commit()
    elif action == "flag" and selected:
        c.execute("INSERT INTO flagged (image) VALUES (?)", (selected,))
        conn.commit()
    return redirect(url_for("index"))

@app.route("/top")
def top_memes():
    c.execute("""
    SELECT winner, COUNT(*) as count FROM votes
    GROUP BY winner ORDER BY count DESC LIMIT 10
    """)
    rows = c.fetchall()
    images = [(get_image_link(row[0]), row[1]) for row in rows]
    return render_template("top.html", images=images)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
