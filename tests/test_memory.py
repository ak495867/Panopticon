import os
import sqlite3
import pytest
from panopticon.memory import PersistentMemory


def test_persistent_memory(tmp_path):
    # Use Pytest's tmp_path to ensure a clean DB per test run
    db_file = tmp_path / "test_memory.db"
    memory = PersistentMemory(db_path=str(db_file))

    # Record seed failures
    memory.record_failure(
        "API missing key exception when booting", "Set your API key using export"
    )
    memory.record_failure(
        "Failed to install numpy version 1.2", "Use pip install numpy==1.24 explicitly"
    )

    # Test TF-IDF keyword extraction
    keywords = memory._extract_keywords("We need to install numpy today")
    assert "install" in keywords
    assert "numpy" in keywords
    assert "today" in keywords
    assert "need" in keywords

    # Test semantic routing retrieval
    results = memory.get_relevant_failures(
        "I am trying to install numpy but it fails continuously"
    )
    assert len(results) >= 1
    assert "pip install numpy" in results[0]["correction"]

    # Test completely irrelevant retrieval (should return empty)
    results_irrelevant = memory.get_relevant_failures(
        "Where is the database located in the folder?"
    )
    assert len(results_irrelevant) == 0
