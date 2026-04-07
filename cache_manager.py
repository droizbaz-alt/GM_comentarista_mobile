import sqlite3
import hashlib
import json
import os
import time

class CacheManager:
    def __init__(self, db_path="analysis_cache.db"):
        # En Vercel el sistema de archivos es de solo lectura excepto /tmp
        if os.environ.get('VERCEL') == '1':
            self.db_path = os.path.join('/tmp', db_path)
            print(f"Serverless environment detected. Using writable path: {self.db_path}")
        else:
            self.db_path = db_path
            
        self.use_memory = False
        self._init_db()

    def _init_db(self):
        """Inicializa la base de datos SQLite. Si falla el archivo, usa memoria."""
        try:
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_model ON commentary_cache (model_name)')
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"SQLite File Error ({self.db_path}): {e}. Falling back to :memory:")
            self.use_memory = True
            self.db_path = ":memory:"
            # Reintentar en memoria
            conn = sqlite3.connect(":memory:")
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
            conn.commit()
            conn.close()

    def _get_hash(self, text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get_commentary(self, prompt):
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
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM commentary_cache")
            count = cursor.fetchone()[0]
            conn.close()
            return {"count": count, "mode": "memory" if self.use_memory else "file"}
        except:
            return {"count": 0, "mode": "error"}

    def clear(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commentary_cache")
            conn.commit()
            conn.close()
            return True
        except:
            return False
