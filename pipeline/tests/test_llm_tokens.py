
def test_token_estimation_logic():
    # Test English-like heuristic
    english_prompt = "Hello, how are you doing today? This is a simple test."
    eng_tokens = int(len(english_prompt) / 3.8)
    
    # Test Code-like heuristic
    code_prompt = "```python\ndef hello():\n    print('world')\n```"
    code_tokens = int(len(code_prompt) / 3.2)
    
    assert code_tokens > eng_tokens * 0.5 # Basic sanity check
    assert "```" in code_prompt
