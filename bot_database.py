import sqlite3
from telethon import Button

DB_PATH = 'meeting_summaries.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            transcription TEXT,
            key_points TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit() 
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def save_transcription(user_id, transcription, key_points):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transcriptions (user_id, transcription, key_points) VALUES (?, ?, ?)
    ''', (user_id, transcription, key_points))
    conn.commit()
    conn.close()

def get_user_transcriptions(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()  
    cursor.execute('''
        SELECT id, user_id, transcription, key_points, created_at 
        FROM transcriptions WHERE user_id = ? 
        ORDER BY id ASC
    ''', (user_id,))
    results = cursor.fetchall() 
    conn.close()

    buttons = []
    for transcription in results:
        meeting_id = transcription[0]
        created_at = transcription[4]
        buttons.append([
            Button.inline(f"Meeting ID {meeting_id}", data=f"view_{meeting_id}"),
            Button.inline(f"View", data=f"view_{meeting_id}"),
            Button.inline(f"Del", data=f"delete_{meeting_id}")
        ])
    buttons.append([Button.inline("List previous meetings", b"list"),Button.inline("Test", b"test")])
    return buttons

def delete_meeting(user_id, meeting_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transcriptions WHERE id = ? and user_id = ?", (meeting_id,user_id))
    conn.commit()
    conn.close()

def view_meeting(user_id, meeting_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT transcription, key_points FROM transcriptions WHERE id = ? and user_id = ?", (meeting_id,user_id))
    transcription = cursor.fetchone()
    conn.close()
    if transcription:
        txt = f"**Viewing Meeting ID {meeting_id}**\n============================\n "
        txt += f"\n**Key Points:**\n {transcription[1]}"
        return txt
    else:
        return "Meeting not found."