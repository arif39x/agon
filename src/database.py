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
            aggressiveness INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def insert_turn(session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness=0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO turns (session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, persona_id, model_name, raw_content, pattern_id, ttft, total_latency, token_count, aggressiveness))
    conn.commit()
    conn.close()
