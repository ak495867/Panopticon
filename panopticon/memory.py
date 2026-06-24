import sqlite3
import os
import re
from typing import List, Dict


class PersistentMemory:
    """Production-grade procedural memory using keyword similarity routing."""

    def __init__(self, db_path="panopticon_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Flaw 3 Fix: Enable WAL and connection timeout for multi-process concurrency
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT,
                    correction TEXT
                )
            """)

    def record_failure(self, reason: str, correction: str):
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.execute(
                "INSERT INTO failures (reason, correction) VALUES (?, ?)",
                (reason, correction),
            )

    def _extract_keywords(self, text: str) -> set:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        return set(words)

    def get_relevant_failures(self, current_context: str, limit=3) -> List[Dict]:
        """Retrieves past failures that have the highest word overlap with the current context."""
        current_keywords = self._extract_keywords(current_context)
        if not current_keywords:
            return []

        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            cursor = conn.execute("SELECT reason, correction FROM failures")
            all_failures = cursor.fetchall()

        scored_failures = []
        for reason, correction in all_failures:
            reason_keywords = self._extract_keywords(reason)
            # Calculate Jaccard-like overlap score
            overlap = len(current_keywords.intersection(reason_keywords))
            if overlap > 0:
                scored_failures.append(
                    (overlap, {"reason": reason, "correction": correction})
                )

        # Sort by highest overlap, then take top N
        scored_failures.sort(key=lambda x: x[0], reverse=True)
        return [f[1] for f in scored_failures[:limit]]
