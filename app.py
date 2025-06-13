import os
import random
import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session, send_file
import dropbox
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supergeheime-session-key'

# Dropbox Setup
DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# DB Setup
conn = sqlite3.connect("votes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS votes (
    image1 TEXT,
    image2 TEXT,
    voted TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS flags (
    image TEXT
)''')
conn.commit()

# Templates
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>memder</title>
    <style>
        body { font-family: 'Comic Sans MS', cursive; text-align: center; }
        .meme-container { display: flex; flex-direction: column; align-items: center; gap: 12px; }
        .meme { border: 3px solid #000; padding: 5px; max-width: 90vw; }
        .btn { font-size: 1.2em; padding: 6px 20px; margin-top: 10px; }
        .smallnote { font-size: 0.7em; margin-top: 20px; color: gray; }
        .topmemes img { border: 2px solid #000; margin: 10px 0; max-width: 90vw; }
    </style>
</head>
<body>
    {% if not session.get('authenticated') %}
        <h2>Zugang nur für echte Meme-Connaisseurs</h2>
        <form method="POST">
            <input type="password" name="password" autofocus placeholder="Passwort">
            <button type="submit">Los!</button>
        </form>
    {% else %}
        {% if meme1 and meme2 %}
            <h3>Welches Meme ist geiler?</h3>
            <div class="meme-container">
                <form method="POST">
                    <input type="hidden" name="image1" value="{{ meme1 }}">
                    <input type="hidden" name="image2" value="{{ meme2 }}">
                    <button name="vote" value="{{ meme1 }}"><img class="meme" src="{{ url_for('get_image', path=meme1) }}"></button>
                    <button name="vote" value="{{ meme2 }}"><img class="meme" src="{{ url_for('get_image', path=meme2) }}"></button>
                </form>
                <form method="POST" style="margin-top: 10px;">
                    <input type="hidden" name="flag1" value="{{ meme1 }}">
                    <input type="hidden" name="flag2" value="{{ meme2 }}">
                    <button name="flag" value="yes">Beide Memes melden 🚩</button>
                </form>
            </div>
        {% endif %}
        <a href="{{ url_for('leaderboard') }}">🔥 Zeig mir die besten Memes!</a>
        <div class="smallnote">Bilder stammen aus den Monaten Januar – Juni 2010</div>
    {% endif %}
</body>
</html>
"""

LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Top Memes</title>
    <style>
        body { font-family: 'Comic Sans MS', cursive; text-align: center; }
        .topmemes img { border: 3px solid #000; margin: 10px 0; max-width: 90vw; }
        .smallnote { font-size: 0.7em; margin-top: 20px; color: gray; }
    </style>
</head>
<body>
    <h2>🔥 Die besten Memes 🔥</h2>
    <div class="topmemes">
        {% for meme in memes %}
            <img src="{{ url_for('get_image', path=meme) }}">
        {% endfor %}
    </div>
    <a href="{{ url_for('index') }}">Zurück</a>
    <div class="smallnote">Bilder stammen aus den Monaten Januar – Juni 2010</div>
</body>
</html>
"""

# Funktionen
def list_images():
    flagged = set(r[0] for r in c.execute("SELECT image FROM flags"))
    entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
    images = [e.path_display for e in entries if isinstance(e, dropbox.files.FileMetadata)]
    return [img for img in images if img not in flagged]

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get('authenticated'):
        if request.method == "POST" and request.form.get("password") == "6969":
            session['authenticated'] = True
            return redirect(url_for('index'))
        return render_template_string(HTML_TEMPLATE, meme1=None, meme2=None)

    if request.method == "POST":
        if 'vote' in request.form:
            c.execute("INSERT INTO votes VALUES (?, ?, ?)", (
                request.form["image1"],
                request.form["image2"],
                request.form["vote"]
            ))
            conn.commit()
        elif 'flag' in request.form:
            c.execute("INSERT INTO flags VALUES (?)", (request.form["flag1"],))
            c.execute("INSERT INTO flags VALUES (?)", (request.form["flag2"],))
            conn.commit()
        return redirect(url_for("index"))

    images = list_images()
    if len(images) < 2:
        return "Zu wenige Memes verfügbar."
    meme1, meme2 = random.sample(images, 2)
    return render_template_string(HTML_TEMPLATE, meme1=meme1, meme2=meme2)

@app.route("/leaderboard")
def leaderboard():
    res = c.execute("SELECT voted, COUNT(*) as votes FROM votes GROUP BY voted ORDER BY votes DESC LIMIT 10")
    memes = [row[0] for row in res.fetchall()]
    return render_template_string(LEADERBOARD_TEMPLATE, memes=memes)

@app.route("/image")
def get_image():
    path = request.args.get("path")
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype='image/jpeg')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
