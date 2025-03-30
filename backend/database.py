import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        phone TEXT UNIQUE,
        password TEXT,
        is_verified INTEGER DEFAULT 0,
        otp TEXT,
        reset_otp TEXT,
        google_id TEXT UNIQUE
    )''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("users.db")

if __name__ == "__main__":
    init_db()