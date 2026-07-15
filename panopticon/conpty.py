import os
import sys
import subprocess
import shutil
import time

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel32 = ctypes.windll.kernel32

    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [
            ("StartupInfo", STARTUPINFOW),
            ("lpAttributeList", wintypes.LPVOID),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    HPCON = wintypes.HANDLE
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016

    class ConPTYProcess:
        def __init__(self, pi, hPC):
            self.pi = pi
            self.hPC = hPC
            self.returncode = None
            self.stdin = None
            self.stdout = None
            self.stderr = None

        def poll(self):
            if self.returncode is not None:
                return self.returncode
            res = kernel32.WaitForSingleObject(self.pi.hProcess, 0)
            if res == 0:  # WAIT_OBJECT_0
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(self.pi.hProcess, ctypes.byref(exit_code)):
                    self.returncode = exit_code.value
                else:
                    self.returncode = 0
                self.cleanup_handles()
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is not None:
                return self.returncode
            if timeout is None:
                ms = 0xFFFFFFFF  # INFINITE
            else:
                ms = int(timeout * 1000)
            res = kernel32.WaitForSingleObject(self.pi.hProcess, ms)
            if res == 0:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(self.pi.hProcess, ctypes.byref(exit_code)):
                    self.returncode = exit_code.value
                else:
                    self.returncode = 0
                self.cleanup_handles()
                return self.returncode
            elif res == 0x00000102:  # WAIT_TIMEOUT
                raise subprocess.TimeoutExpired(self.pi.dwProcessId, timeout)
            return self.returncode

        def terminate(self):
            if self.poll() is None:
                kernel32.TerminateProcess(self.pi.hProcess, 1)

        def kill(self):
            self.terminate()

        def send_signal(self, sig):
            pass

        def cleanup_handles(self):
            if getattr(self, "pi", None) and self.pi.hProcess:
                kernel32.CloseHandle(self.pi.hProcess)
                self.pi.hProcess = 0
            if getattr(self, "pi", None) and self.pi.hThread:
                kernel32.CloseHandle(self.pi.hThread)
                self.pi.hThread = 0

    def spawn_conpty(command, env=None):
        in_read, in_write = os.pipe()
        out_read, out_write = os.pipe()

        hInputRead = msvcrt.get_osfhandle(in_read)
        hOutputWrite = msvcrt.get_osfhandle(out_write)

        size = COORD(120, 30)
        hPC = HPCON()
        res = kernel32.CreatePseudoConsole(size, hInputRead, hOutputWrite, 0, ctypes.byref(hPC))
        if res != 0:
            os.close(in_read)
            os.close(in_write)
            os.close(out_read)
            os.close(out_write)
            raise RuntimeError(f"CreatePseudoConsole failed with HRESULT {res}")

        attr_list_size = ctypes.c_size_t(0)
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_list_size))
        attr_list = ctypes.create_string_buffer(attr_list_size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, ctypes.byref(attr_list_size)):
            kernel32.ClosePseudoConsole(hPC)
            raise RuntimeError("InitializeProcThreadAttributeList failed")

        if not kernel32.UpdateProcThreadAttribute(
            attr_list,
            0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            hPC,
            ctypes.sizeof(HPCON),
            None,
            None,
        ):
            kernel32.DeleteProcThreadAttributeList(attr_list)
            kernel32.ClosePseudoConsole(hPC)
            raise RuntimeError("UpdateProcThreadAttribute failed")

        si_ex = STARTUPINFOEXW()
        si_ex.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
        si_ex.lpAttributeList = ctypes.cast(attr_list, wintypes.LPVOID)

        pi = PROCESS_INFORMATION()

        exe = shutil.which(command[0]) or command[0]
        cmdline = subprocess.list2cmdline([exe] + command[1:])
        cmd_buf = ctypes.create_unicode_buffer(cmdline)

        env_buf = None
        flags = EXTENDED_STARTUPINFO_PRESENT
        if env is not None:
            env_items = [f"{str(k)}={str(v)}" for k, v in env.items()]
            env_str = "\0".join(sorted(env_items)) + "\0\0"
            env_buf = ctypes.create_unicode_buffer(env_str)
            flags |= CREATE_UNICODE_ENVIRONMENT

        success = kernel32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            flags,
            env_buf,
            None,
            ctypes.byref(si_ex),
            ctypes.byref(pi),
        )

        kernel32.DeleteProcThreadAttributeList(attr_list)
        os.close(in_read)
        os.close(out_write)

        if not success:
            err = kernel32.GetLastError()
            kernel32.ClosePseudoConsole(hPC)
            os.close(in_write)
            os.close(out_read)
            raise RuntimeError(f"CreateProcessW failed with error {err}")

        proc = ConPTYProcess(pi, hPC)
        return proc, hPC, in_write, out_read

    def close_conpty(hPC):
        if hPC:
            try:
                kernel32.ClosePseudoConsole(hPC)
            except Exception:
                pass
else:
    def spawn_conpty(command, env=None):
        raise NotImplementedError("ConPTY is only supported on Windows")

    def close_conpty(hPC):
        pass
