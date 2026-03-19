import sqlite3
import hashlib
import json
import os
import time

class CacheManager:
    def __init__(self, db_path="analysis_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database and creates the cache table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commentary_cache (
                prompt_hash TEXT PRIMARY KEY,
                model_name TEXT,
                prompt_text TEXT,
                response_text TEXT,
                timestamp REAL
            )
        ''')
        # Index for faster lookup by model name if needed
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model ON commentary_cache (model_name)')
        conn.commit()
        conn.close()

    def _get_hash(self, text):
        """Generates a SHA-256 hash for the given text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get_commentary(self, prompt):
        """Retrieves cached commentary for a specific prompt."""
        prompt_hash = self._get_hash(prompt)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_text FROM commentary_cache WHERE prompt_hash = ?", 
                (prompt_hash,)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            print(f"Cache lookup error: {e}")
            return None

    def save_commentary(self, prompt, model_name, response):
        """Saves a prompt and its response to the cache."""
        prompt_hash = self._get_hash(prompt)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO commentary_cache 
                (prompt_hash, model_name, prompt_text, response_text, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (prompt_hash, model_name, prompt, response, time.time()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Cache save error: {e}")
            return False

    def get_stats(self):
        """Returns basic statistics about the cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM commentary_cache")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(LENGTH(response_text)) FROM commentary_cache")
            total_chars = cursor.fetchone()[0] or 0
            conn.close()
            return {
                "count": count,
                "size_kb": round(total_chars / 1024, 2)
            }
        except:
            return {"count": 0, "size_kb": 0}

    def clear(self):
        """Clears all entries in the cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commentary_cache")
            conn.commit()
            conn.close()
            return True
        except:
            return False
