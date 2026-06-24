from panopticon.cli import strip_ansi

def test_strip_ansi():
    # Basic red color text
    colored_text = "\x1b[31mFatal Error\x1b[0m: File not found"
    assert strip_ansi(colored_text) == "Fatal Error: File not found"
    
    # Complex formatting (Bold + Green)
    complex_text = "\x1b[1m\x1b[32mSuccess\x1b[0m"
    assert strip_ansi(complex_text) == "Success"
    
    # Loading spinner edge case
    spinner_text = "\x1b[?25l\x1b[2K\x1b[1G⠋ Loading..."
    assert "Loading..." in strip_ansi(spinner_text)
