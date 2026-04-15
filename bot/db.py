import sqlite3

DB_PATH = "/data/data.db"  # Railway用（ローカルなら "data.db"）

# =========================
# 接続
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# =========================
# 初期化
# =========================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        guild_id TEXT,
        user_id TEXT,
        role_name TEXT,
        color TEXT,
        target TEXT,
        weight REAL,
        role_id INTEGER,
        enabled INTEGER DEFAULT 1,
        PRIMARY KEY (guild_id, user_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        guild_id TEXT,
        winner_id TEXT,
        role_name TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operators (
        guild_id TEXT,
        user_id TEXT,
        PRIMARY KEY (guild_id, user_id)
    )
    """)

    conn.commit()
    conn.close()

# =========================
# entries
# =========================
def get_entries(guild_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM entries WHERE guild_id=?", (guild_id,))
    rows = cur.fetchall()
    conn.close()

    data = {}
    for r in rows:
        data[r[1]] = {
            "role_name": r[2],
            "color": r[3],
            "target": r[4],
            "weight": r[5],
            "role_id": r[6],
            "enabled": r[7] if len(r) > 7 else 1
        }
    return data

def save_entry(guild_id, user_id, entry):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        guild_id,
        user_id,
        entry["role_name"],
        entry["color"],
        entry["target"],
        entry["weight"],
        entry.get("role_id"),
        entry.get("enabled", 1) or 1
    ))

    conn.commit()
    conn.close()

def delete_entry(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM entries WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    conn.commit()
    conn.close()

# =========================
# history
# =========================
def add_history(guild_id, winner_id, role_name):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO history (guild_id, winner_id, role_name)
    VALUES (?, ?, ?)
    """, (guild_id, winner_id, role_name))

    conn.commit()
    conn.close()

def get_history(guild_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT winner_id, role_name FROM history
    WHERE guild_id=? ORDER BY ts DESC LIMIT 10
    """, (guild_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

# =========================
# operators
# =========================
def add_operator(guild_id, user_id):
    ops = get_operators(guild_id)
    if user_id in ops:
        return
    
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO operators VALUES (?, ?)
    """, (guild_id, user_id))

    conn.commit()
    conn.close()

def remove_operator(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM operators WHERE guild_id=? AND user_id=?
    """, (guild_id, user_id))

    conn.commit()
    conn.close()

def is_operator(guild_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT 1 FROM operators WHERE guild_id=? AND user_id=?
    """, (guild_id, user_id))

    result = cur.fetchone()
    conn.close()

    return result is not None

def get_operators(guild_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM operators WHERE guild_id=?", (guild_id,))
    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]
