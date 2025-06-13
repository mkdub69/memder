import os
import random
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, send_file
import dropbox
from io import BytesIO

app = Flask(__name__)

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_FOLDER_PATH = "/memder"

dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# DB setup
DB_PATH = "votes.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS votes (
                image TEXT,
                score INTEGER DEFAULT 0
            )''')
c.execute('''CREATE TABLE IF NOT EXISTS flagged (
                image TEXT
            )''')
conn.commit()

# list images excluding flagged
def list_images():
    entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
    images = [entry.path_lower for entry in entries if isinstance(entry, dropbox.files.FileMetadata)]
    c.execute("SELECT image FROM flagged")
    flagged = {row[0] for row in c.fetchall()}
    return [img for img in images if img not in flagged]

# serve image from dropbox
@app.route('/image')
def image():
    path = request.args.get('path')
    metadata, res = dbx.files_download(path)
    return send_file(BytesIO(res.content), mimetype='image/jpeg')

# main page
@app.route('/')
def index():
    images = list_images()
    if len(images) < 2:
        return "Nicht genug Memes zum Anzeigen."
    pair = random.sample(images, 2)
    return render_template_string(TEMPLATE, image1=pair[0], image2=pair[1])

# voting
@app.route('/vote', methods=['POST'])
def vote():
    image = request.form['image']
    c.execute("INSERT INTO votes (image, score) VALUES (?, 1) ON CONFLICT(image) DO UPDATE SET score = score + 1", (image,))
    conn.commit()
    return redirect(url_for('index'))

# flagging
@app.route('/flag', methods=['POST'])
def flag():
    image = request.form['image']
    c.execute("INSERT OR IGNORE INTO flagged (image) VALUES (?)", (image,))
    conn.commit()
    return redirect(url_for('index'))

# leaderboard
@app.route('/leaderboard')
def leaderboard():
    c.execute("SELECT image, score FROM votes ORDER BY score DESC LIMIT 10")
    results = c.fetchall()
    return render_template_string(LEADERBOARD_TEMPLATE, results=results)

# HTML Templates
TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>Memder</title>
    <style>
        body {
            font-family: "Comic Sans MS", cursive, sans-serif;
            text-align: center;
        }
        .meme-container {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            margin: 20px;
        }
        .meme-box {
            margin: 10px;
            border: 2px solid #888;
            padding: 10px;
            max-width: 45%;
        }
        img {
            max-width: 100%;
            height: auto;
        }
        button {
            margin: 5px;
            padding: 10px;
        }
        .footer {
            font-size: 0.8em;
            color: gray;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h2>Welches Meme ist geiler?</h2>
    <div class="meme-container">
        <div class="meme-box">
            <img src="/image?path={{ image1 }}" alt="Meme 1">
            <form method="post" action="/vote">
                <input type="hidden" name="image" value="{{ image1 }}">
                <button type="submit">Wählen</button>
            </form>
            <form method="post" action="/flag">
                <input type="hidden" name="image" value="{{ image1 }}">
                <button type="submit">Melden</button>
            </form>
        </div>
        <div class="meme-box">
            <img src="/image?path={{ image2 }}" alt="Meme 2">
            <form method="post" action="/vote">
                <input type="hidden" name="image" value="{{ image2 }}">
                <button type="submit">Wählen</button>
            </form>
            <form method="post" action="/flag">
                <input type="hidden" name="image" value="{{ image2 }}">
                <button type="submit">Melden</button>
            </form>
        </div>
    </div>
    <a href="/leaderboard">Top 10 Memes anzeigen</a>
    <div class="footer">Zeitraum: Januar – Juni 2010</div>
</body>
</html>
'''

LEADERBOARD_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>Top Memes</title>
    <style>
        body {
            font-family: "Comic Sans MS", cursive, sans-serif;
            text-align: center;
        }
        .meme {
            margin: 20px;
        }
        img {
            max-width: 90%;
            height: auto;
            border: 2px solid #888;
        }
        .footer {
            font-size: 0.8em;
            color: gray;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h2>Top 10 Memes</h2>
    {% for image, score in results %}
        <div class="meme">
            <img src="/image?path={{ image }}" alt="Meme">
            <p>{{ score }} Votes</p>
        </div>
    {% endfor %}
    <a href="/">Zurück zur Auswahl</a>
    <div class="footer">Zeitraum: Januar – Juni 2010</div>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True)
