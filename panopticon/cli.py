import subprocess
import threading
import sys
import time
import argparse
import re
import os
import signal
import codecs
import atexit
from typing import List
from .observer import PanopticonObserver, InterventionException
from .policies import AdversarialLogicCheck, AntiLoopPolicy, BlacklistPolicy


def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class CLIWrapper:
    def __init__(self, command: List[str]):
        self.command = command
        target_agent = self.command[0] if self.command else "unknown"

        self.observer = PanopticonObserver(
            policies=[
                BlacklistPolicy(forbidden_patterns=["rm -rf /", "DROP TABLE"]),
                AntiLoopPolicy(window=3, threshold=0.85),
                AdversarialLogicCheck(target_agent=target_agent),
            ]
        )

        self.process = None
        self.buffer = []
        self.running = False
        self.lock = threading.Lock()
        self.threads = []

    def run(self):
        self.running = True
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["FORCE_COLOR"] = "1"
        env["CLICOLOR_FORCE"] = "1"

        print(f"[PANOPTICON] Booting Immune System for: {' '.join(self.command)}")
        print(
            f"[PANOPTICON] Policies Active: Blacklist, AntiLoop (Fuzzy), AdversarialLogic"
        )

        # Flaw 2 Fix: Removing text=True to read raw binary bytes
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            bufsize=0,
            env=env,
        )

        t_out = threading.Thread(target=self._read_stdout, daemon=True)
        t_out.start()
        self.threads.append(t_out)

        t_in = threading.Thread(target=self._forward_stdin, daemon=True)
        t_in.start()
        self.threads.append(t_in)

        t_eval = threading.Thread(target=self._eval_loop, daemon=True)
        t_eval.start()
        self.threads.append(t_eval)

        # Register cleanup on exit
        atexit.register(self._cleanup)

        try:
            self.process.wait()
        finally:
            self.running = False
            self._cleanup()

    def _cleanup(self):
        """Cleanly shutdown all threads and resources."""
        self.running = False

        # Close subprocess pipes
        if self.process:
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
            except Exception:
                pass

            try:
                if self.process.stdout and not self.process.stdout.closed:
                    self.process.stdout.close()
            except Exception:
                pass

            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            except Exception:
                pass

        # Wait for threads with timeout
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)

    def _forward_stdin(self):
        """Forward stdin to subprocess, with non-blocking checks."""
        try:
            while self.running and self.process and self.process.poll() is None:
                try:
                    # Windows-safe non-blocking stdin read
                    if sys.platform == "win32":
                        # On Windows, use a small sleep to avoid 100% CPU
                        time.sleep(0.05)
                        # Try non-blocking read using a different approach
                        if sys.stdin and not sys.stdin.closed:
                            try:
                                # This will still block, but with timeout via select on Unix
                                line = sys.stdin.buffer.readline()
                                if line:
                                    if self.process.stdin and not self.process.stdin.closed:
                                        self.process.stdin.write(line)
                                        self.process.stdin.flush()
                                else:
                                    break  # EOF
                            except (EOFError, OSError, ValueError):
                                break
                    else:
                        # Unix/Linux: use select for non-blocking check
                        import select

                        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if ready:
                            line = sys.stdin.buffer.readline()
                            if line:
                                if self.process.stdin and not self.process.stdin.closed:
                                    self.process.stdin.write(line)
                                    self.process.stdin.flush()
                            else:
                                break  # EOF
                except (EOFError, OSError, ValueError, BrokenPipeError):
                    break
        except Exception:
            pass
        finally:
            try:
                if self.process and self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
            except Exception:
                pass

    def _read_stdout(self):
        # Flaw 2 Fix: Safely decode multi-byte UTF-8 emojis incrementally
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while self.running and self.process and self.process.poll() is None:
                try:
                    byte_chunk = self.process.stdout.read(1)
                    if not byte_chunk:
                        break

                    # Mirror raw bytes to actual terminal seamlessly
                    sys.stdout.buffer.write(byte_chunk)
                    sys.stdout.buffer.flush()

                    char_str = decoder.decode(byte_chunk)
                    if char_str:
                        with self.lock:
                            self.buffer.append(char_str)
                except (OSError, ValueError, BrokenPipeError):
                    break
        except Exception:
            pass
        finally:
            try:
                if self.process and self.process.stdout and not self.process.stdout.closed:
                    self.process.stdout.close()
            except Exception:
                pass

    def _eval_loop(self):
        while self.running and self.process and self.process.poll() is None:
            time.sleep(15)

            with self.lock:
                if not self.buffer:
                    continue
                full_text = "".join(self.buffer)

                # Flaw 1 Fix: Sliding window overlap to prevent bridging blindness
                overlap = full_text[-100:] if len(full_text) > 100 else ""
                self.buffer.clear()
                if overlap:
                    self.buffer.append(overlap)

            clean_text = strip_ansi(full_text)
            self.observer.log_action(
                "CLI_Agent", clean_text, "cli_execution", len(clean_text) // 4
            )

            try:
                self.observer._evaluate_state("CLI_Agent")
            except InterventionException as e:
                print(f"\n\n[PANOPTICON GUILLOTINE TRIGGERED]")
                print(f"[REASON]: {e.args[0]}")
                print(
                    f"[LIVE INJECTION]: Interrupting agent and injecting correction...\n"
                )

                # Flaw 1 Fix: The "Unkillable Zombie" SIGINT Interrupt
                try:
                    if sys.platform != "win32":
                        self.process.send_signal(signal.SIGINT)
                    # Give the agent a split second to catch the interrupt before writing to stdin
                    time.sleep(0.5)
                except Exception:
                    pass

                try:
                    # Write the injection payload as binary
                    if self.process.stdin and not self.process.stdin.closed:
                        payload = (e.course_correction + "\n").encode("utf-8")
                        self.process.stdin.write(payload)
                        self.process.stdin.flush()
                except Exception as ex:
                    print(
                        f"[ERROR] Live injection failed or agent deadlocked: {ex}. Hard terminating."
                    )
                    self.process.terminate()
                    self.running = False
                    break


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(
        description="Panopticon: Production-Grade Immune System for AI CLIs"
    )
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="The command to run, e.g., 'claude'"
    )
    args = parser.parse_args()

    if not args.command:
        print("Usage: panopticon [command]")
        sys.exit(1)

    wrapper = CLIWrapper(args.command)
    try:
        wrapper.run()
    except KeyboardInterrupt:
        print("\n[PANOPTICON] Interrupted by user. Cleaning up...")
        wrapper._cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"[PANOPTICON ERROR] {e}")
        wrapper._cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
