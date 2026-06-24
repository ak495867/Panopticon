from panopticon.policies import BlacklistPolicy, AntiLoopPolicy

def test_blacklist_policy():
    policy = BlacklistPolicy(["rm -rf /", "DROP TABLE"])
    
    # Should trigger on exact matches and contained strings
    is_violating, reason, correction = policy.evaluate([{"thought": "I will run rm -rf / now to clean up"}])
    assert is_violating == True
    assert "rm -rf /" in reason
    
    # Should pass normally
    is_violating, _, _ = policy.evaluate([{"thought": "I will run ls -la"}])
    assert is_violating == False

def test_antiloop_policy():
    policy = AntiLoopPolicy(window=3, threshold=0.85)
    
    # Not enough data (window is 3)
    assert policy.evaluate([{"thought": "hello"}, {"thought": "hello"}])[0] == False
    
    # Exact match loop
    stream = [{"thought": "Reading file A"}, {"thought": "Reading file A"}, {"thought": "Reading file A"}]
    assert policy.evaluate(stream)[0] == True
    
    # Fuzzy match loop (differing by small timestamp or loading spinner)
    stream_fuzzy = [
        {"thought": "Reading file A [10:01] /"}, 
        {"thought": "Reading file A [10:02] -"}, 
        {"thought": "Reading file A [10:03] \\"}
    ]
    assert policy.evaluate(stream_fuzzy)[0] == True
    
    # Normal execution (no loop)
    stream_normal = [{"thought": "Reading A"}, {"thought": "Writing B"}, {"thought": "Testing C"}]
    assert policy.evaluate(stream_normal)[0] == False
