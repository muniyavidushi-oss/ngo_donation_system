import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---------------- USERS TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    aadhaar TEXT,
    role TEXT DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

# ---------------- DONATIONS TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
""")

# ---------------- LOGIN LOGS TABLE ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
""")

# ---------------- FIX EXISTING DATA ----------------
# Fill NULL created_at values in donations table
cur.execute("""
    UPDATE donations 
    SET created_at = CURRENT_TIMESTAMP 
    WHERE created_at IS NULL OR created_at = ''
""")
print(f"✅ Updated {cur.rowcount} donation records with dates")

# Fill NULL created_at values in login_logs table
cur.execute("""
    UPDATE login_logs 
    SET created_at = CURRENT_TIMESTAMP 
    WHERE created_at IS NULL OR created_at = ''
""")
print(f"✅ Updated {cur.rowcount} login records with dates")

conn.commit()
conn.close()

print("Database and tables created successfully")
