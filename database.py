import sqlite3

DB_PATH = "consortium_research.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS turns (
            turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            persona_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            pattern_id TEXT NOT NULL,
            ttft REAL NOT NULL,
            total_latency REAL NOT NULL,
            token_count INTEGER NOT NULL,
            aggressiveness INTEGER DEFAULT 0,
            happy INTEGER DEFAULT 0,
            angry INTEGER DEFAULT 0,
            sad INTEGER DEFAULT 0,
            disrespect INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def insert_turn(session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness=0, happy=0, angry=0, sad=0, disrespect=0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO turns (session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness, happy, angry, sad, disrespect)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness, happy, angry, sad, disrespect))
    conn.commit()
    conn.close()

def get_turns(session_id=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if session_id:
        cursor.execute("SELECT * FROM turns WHERE session_id = ? ORDER BY turn_id ASC", (session_id,))
    else:
        cursor.execute("SELECT * FROM turns ORDER BY turn_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
