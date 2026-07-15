import io
import sys

from panopticon.cli import CLIWrapper, strip_ansi


class DummyStdinStream:
    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)


class DummyProcessStdin:
    def __init__(self):
        self.written = bytearray()
        self.closed = False

    def write(self, data: bytes):
        self.written.extend(data)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class DummyProcess:
    def __init__(self):
        self.stdin = DummyProcessStdin()
        self.stdout = io.BytesIO()

    def poll(self):
        return None


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


def test_read_stdin_forwards_input():
    wrapper = CLIWrapper(["dummy"])
    wrapper.running = True
    wrapper.process = DummyProcess()

    original_stdin = sys.stdin
    try:
        sys.stdin = DummyStdinStream(b"hello world\n")
        wrapper._read_stdin()
    finally:
        sys.stdin = original_stdin

    assert wrapper.process.stdin.written == b"hello world\n"
    assert wrapper.process.stdin.closed is True
