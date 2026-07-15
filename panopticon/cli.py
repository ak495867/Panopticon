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
        self.master_fd = None
        self.master_fd_in = None
        self.conpty_hPC = None
        self.buffer = []
        self.running = False
        self.lock = threading.Lock()
        self.threads = []
        self._stop_event = threading.Event()

    def run(self):
        self.running = True
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["FORCE_COLOR"] = "1"
        env["CLICOLOR_FORCE"] = "1"

        print(f"[PANOPTICON] Booting Immune System for: {' '.join(self.command)}")
        print(
            f"[PANOPTICON] Policies Active: Blacklist, AntiLoop (Fuzzy), "
            f"AdversarialLogic"
        )

        use_pty = (
            sys.platform != "win32"
            and sys.stdin is not None
            and sys.stdin.isatty()
            and sys.stdout.isatty()
        )
        use_conpty = (
            sys.platform == "win32"
            and sys.stdin is not None
            and sys.stdin.isatty()
            and sys.stdout.isatty()
        )
        self.master_fd = None
        self.master_fd_in = None
        self.conpty_hPC = None

        if use_pty:
            import pty

            master_fd, slave_fd = pty.openpty()
            self.master_fd = master_fd
            self.master_fd_in = master_fd
            self.process = subprocess.Popen(
                self.command,
                stdout=slave_fd,
                stderr=slave_fd,
                stdin=slave_fd,
                bufsize=0,
                env=env,
                close_fds=True,
            )
            os.close(slave_fd)
            use_stdin_thread = True
        elif use_conpty:
            from panopticon.conpty import spawn_conpty

            proc, hPC, master_in, master_out = spawn_conpty(self.command, env=env)
            self.process = proc
            self.conpty_hPC = hPC
            self.master_fd = master_out
            self.master_fd_in = master_in
            use_stdin_thread = True
        else:
            stdin_target = subprocess.PIPE
            use_stdin_thread = True

            if sys.platform != "win32" and sys.stdin is not None and sys.stdin.isatty():
                stdin_target = sys.stdin
                use_stdin_thread = False

            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=stdin_target,
                bufsize=0,
                env=env,
            )

        t_out = threading.Thread(target=self._read_stdout, daemon=True)
        t_out.start()
        self.threads.append(t_out)

        t_eval = threading.Thread(target=self._eval_loop, daemon=True)
        t_eval.start()
        self.threads.append(t_eval)

        if use_stdin_thread:
            t_in = threading.Thread(target=self._read_stdin, daemon=True)
            t_in.start()
            self.threads.append(t_in)

        # Register cleanup on exit
        atexit.register(self._cleanup)

        try:
            self.process.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self._cleanup()

    def _cleanup(self):
        """Cleanly shutdown all threads and resources."""
        self.running = False
        self._stop_event.set()

        if getattr(self, "conpty_hPC", None) is not None:
            try:
                from panopticon.conpty import close_conpty

                close_conpty(self.conpty_hPC)
            except Exception:
                pass
            self.conpty_hPC = None

        if getattr(self, "master_fd_in", None) is not None:
            try:
                if self.master_fd_in != getattr(self, "master_fd", None):
                    os.close(self.master_fd_in)
            except Exception:
                pass
            self.master_fd_in = None

        if getattr(self, "master_fd", None) is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        # Close subprocess pipes FIRST before thread cleanup
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

    def _read_stdout(self):
        # Flaw 2 Fix: Safely decode multi-byte UTF-8 emojis incrementally
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while self.running and self.process and self.process.poll() is None:
                try:
                    if getattr(self, "master_fd", None) is not None:
                        byte_chunk = os.read(self.master_fd, 1)
                    else:
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
                if (
                    getattr(self, "master_fd", None) is None
                    and self.process
                    and self.process.stdout
                    and (not self.process.stdout.closed)
                ):
                    self.process.stdout.close()
            except Exception:
                pass

    def _stdin_ready(self) -> bool:
        if sys.platform == "win32":
            if (
                sys.stdin is not None
                and getattr(sys.stdin, "isatty", lambda: False)()
                and hasattr(sys.stdin, "fileno")
            ):
                try:
                    import msvcrt

                    return msvcrt.kbhit()
                except ImportError:
                    return False
            return True
        else:
            import select

            try:
                rlist, _, _ = select.select([sys.stdin], [], [], 0)
                return bool(rlist)
            except Exception:
                return False

    def _read_stdin(self):
        if sys.platform == "win32":
            if (
                sys.stdin is not None
                and getattr(sys.stdin, "isatty", lambda: False)()
                and hasattr(sys.stdin, "fileno")
                and sys.stdin.fileno() == 0
            ):
                self._read_stdin_windows()
                return

        stdin_buffer = getattr(sys.stdin, "buffer", None)
        if stdin_buffer is None:
            return

        try:
            while (
                self.running
                and self.process
                and self.process.poll() is None
                and not self._stop_event.is_set()
            ):
                if not self._stdin_ready():
                    time.sleep(0.1)
                    continue

                try:
                    read_func = getattr(stdin_buffer, "read1", stdin_buffer.read)
                    data = read_func(1024)
                    if not data:
                        break
                    if getattr(self, "master_fd_in", None) is not None:
                        os.write(self.master_fd_in, data)
                    elif getattr(self, "master_fd", None) is not None:
                        os.write(self.master_fd, data)
                    elif self.process.stdin and not self.process.stdin.closed:
                        self.process.stdin.write(data)
                        self.process.stdin.flush()
                except (OSError, ValueError, BrokenPipeError):
                    break
        except Exception:
            pass
        finally:
            try:
                if (
                    getattr(self, "master_fd", None) is None
                    and self.process
                    and self.process.stdin
                    and (not self.process.stdin.closed)
                ):
                    self.process.stdin.close()
            except Exception:
                pass

    def _read_stdin_windows(self):
        try:
            import msvcrt
        except ImportError:
            return

        try:
            while (
                self.running
                and self.process
                and self.process.poll() is None
                and not self._stop_event.is_set()
            ):
                if not msvcrt.kbhit():
                    time.sleep(0.1)
                    continue

                try:
                    char = msvcrt.getwch()
                    if char == "\x03":
                        if self.process.poll() is None:
                            try:
                                self.process.send_signal(signal.CTRL_C_EVENT)
                            except Exception:
                                pass
                        continue

                    data = char.encode("utf-8")
                    if getattr(self, "master_fd_in", None) is not None:
                        os.write(self.master_fd_in, data)
                    elif getattr(self, "master_fd", None) is not None:
                        os.write(self.master_fd, data)
                    elif self.process.stdin and not self.process.stdin.closed:
                        self.process.stdin.write(data)
                        self.process.stdin.flush()
                except (OSError, ValueError, BrokenPipeError):
                    break
        except Exception:
            pass
        finally:
            try:
                if (
                    self.process
                    and self.process.stdin
                    and (not self.process.stdin.closed)
                ):
                    self.process.stdin.close()
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
                    f"[LIVE INJECTION]: Interrupting agent and injecting "
                    f"correction...\n"
                )

                # Flaw 1 Fix: The "Unkillable Zombie" SIGINT Interrupt
                try:
                    if sys.platform != "win32":
                        self.process.send_signal(signal.SIGINT)
                    # Give the agent a split second to catch the interrupt
                    time.sleep(0.5)
                except Exception:
                    pass

                try:
                    # Write the injection payload as binary
                    payload = (e.course_correction + "\n").encode("utf-8")
                    if getattr(self, "master_fd_in", None) is not None:
                        os.write(self.master_fd_in, payload)
                    elif getattr(self, "master_fd", None) is not None:
                        os.write(self.master_fd, payload)
                    elif self.process.stdin and not self.process.stdin.closed:
                        self.process.stdin.write(payload)
                        self.process.stdin.flush()
                except Exception as ex:
                    print(
                        f"[ERROR] Live injection failed or agent deadlocked: "
                        f"{ex}. Hard terminating."
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
