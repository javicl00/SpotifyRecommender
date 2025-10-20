import sqlite3
import json
import os

DB_PATH = "usuarios.db"


def init_db():
    if not os.path.exists(DB_PATH):  # Solo crearlo una vez
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                email TEXT,
                likes TEXT,
                dislikes TEXT,
                last_update TEXT
            )
        """
        )
        conn.commit()
        conn.close()


def save_user_profile(user_id, email, likes, dislikes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "REPLACE INTO user_profiles (id, email, likes, dislikes, last_update) VALUES (?, ?, ?, ?, datetime('now'))",
        (user_id, email, json.dumps(likes), json.dumps(dislikes)),
    )
    conn.commit()
    conn.close()


def load_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT email, likes, dislikes, last_update FROM user_profiles WHERE id=?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "email": row[0],
            "likes": json.loads(row[1]),
            "dislikes": json.loads(row[2]),
            "last_update": row[3],
        }
    return None
