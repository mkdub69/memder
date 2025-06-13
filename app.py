import os
import random
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session
import dropbox
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'super_secret_key'

DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
DROPBOX_FOLDER_PATH = '/memder'
DATABASE = 'votes.db'
PASSWORD = '6969'

dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# Template
HTML = '''
<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>Memder Voting</title>
    <style>
        body {
            font-family: "Comic Sans MS", cursive, sans-serif;
            text-align: center;
            background: #fff;
            margin: 0;
            padding: 0;
        }
        h2 {
            font-size: 1.2em;
            margin-top: 20px;
        }
        .meme-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 10px;
        }
        .meme {
            border: 2px solid #ccc;
            padding: 5px;
            max-width: 95vw;
        }
        .btn-row {
            margin-top: 10px;
        }
        .small {
            font-size: 0.7em;
            margin-top: 20px;
            color: gray;
        }
        a {
            font-size: 0.9em;
        }
        form {
            margin: 0;
        }
    </style>
</head>
<body>
    {% if not session.get('authenticated') %}
        <h2>Passwort eingeben</h2>
        <form method="post" action="{{ url_for('login') }}">
            <input type="password" name="password">
            <input type="submit" value="Los">
        </form>
    {% else %}
        <h2>Welches Meme ist geiler?</h2>
        <div class="meme-container">
            <form method="post">
                <div><img class="meme" src="{{ url_for('serve_image', path=left_path) }}"></div>
                <div class="btn-row">
                    <button name="vote" value="{{ left_path }}">Linkes Meme ist geiler</button>
                    <button name="flag" value="{{ left_path }}">Meme melden</button>
                </div>
            </form>

            <form method="post">
                <div><img class="meme" src="{{ url_for('serve_image', path=right_path) }}"></div>
                <div class="btn-row">
                    <button name="vote" value="{{ right_path }}">Rechtes Meme ist geiler</button>
                    <button name="flag" value="{{ right_path }}">Meme melden</button>
                </div>
            </form>
        </div>
        <a href="{{ url_for('leaderboard') }}">🔥 Beste Memes anzeigen</a>
        <div class="small">Meme-Zeitraum: Januar – Juni 2010</div>
    {% endif %}
</body>
</html>
'''

# Helper
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS votes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        image TEXT,
                        count INTEGER DEFAULT 1
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS flagged (
                        image TEXT PRIMARY KEY
                    )''')
        conn.commit()

def list_images():
    try:
        entries = dbx.files_list_folder(DROPBOX_FOLDER_PATH).entries
        with sqlite3.connect(DATABASE) as conn:
            flagged = {row[0] for row in conn.execute("SELECT image FROM flagged")}
        return [e.path_lower for e in entries if isinstance(e, dropbox.files.FileMetadata) and e.path_lower not in flagged]
    except Exception as e:
        print("Fehler beim Abrufen von Bildern:", e)
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('authenticated'):
        return render_template_string(HTML)

    if request.method == 'POST':
        if 'vote' in request.form:
            voted = request.form['vote']
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO votes (image, count) VALUES (?, 1) ON CONFLICT(image) DO UPDATE SET count = count + 1", (voted,))
                conn.commit()
        elif 'flag' in request.form:
            flagged = request.form['flag']
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO flagged (image) VALUES (?)", (flagged,))
                conn.commit()
        return redirect(url_for('index'))

    images = list_images()
    if len(images) < 2:
        return "<h2>Zu wenige Memes verfügbar.</h2>"

    left, right = random.sample(images, 2)
    return render_template_string(HTML, left_path=left, right_path=right)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == PASSWORD:
        session['authenticated'] = True
    return redirect(url_for('index'))

@app.route('/leaderboard')
def leaderboard():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT image, count FROM votes ORDER BY count DESC LIMIT 10")
        rows = c.fetchall()
    html = '<h2>🔥 Beste Memes</h2><div style="font-family:Comic Sans MS">'
    for row in rows:
        html += f'<div style="margin-bottom:20px;"><img style="max-width:95vw;border:2px solid #ccc;" src="/image?path={quote(row[0])}"><br>Votes: {row[1]}</div>'
    html += '<br><a href="/">Zurück zur Auswahl</a>'
    html += '<div class="small">Meme-Zeitraum: Januar – Juni 2010</div>'
    html += '</div>'
    return html

@app.route('/image')
def serve_image():
    path = request.args.get('path')
    _, res = dbx.files_download(path)
    return res.content, 200, {'Content-Type': 'image/jpeg'}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
