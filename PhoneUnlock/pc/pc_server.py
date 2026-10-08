"""
Phone Unlock - PC side (Windows).
Must run as SYSTEM inside your desktop session (start_server.bat does this with PsExec),
otherwise it cannot type on the lock screen.
Only standard-library Python is used.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import hmac
import json
import os
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

SECRET = CFG["secret"].encode()
PASSWORD = CFG["password"]
PORT = int(CFG.get("port", 8765))
if CFG["secret"].startswith("CHANGE_ME") or CFG["password"].startswith("CHANGE_ME"):
    sys.exit("Edit config.json first (secret and password).")

# ---------- Win32 plumbing ----------
user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_SHIFT = 0x10
VK_RETURN = 0x0D


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _U)]


user32.OpenInputDesktop.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
user32.OpenInputDesktop.restype = wt.HANDLE
user32.SetThreadDesktop.argtypes = [wt.HANDLE]
user32.SetThreadDesktop.restype = wt.BOOL
user32.CloseDesktop.argtypes = [wt.HANDLE]
user32.CloseDesktop.restype = wt.BOOL
user32.GetUserObjectInformationW.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                             wt.DWORD, ctypes.POINTER(wt.DWORD)]
user32.GetUserObjectInformationW.restype = wt.BOOL
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wt.UINT


def _send(vk=0, scan=0, flags=0):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_vk(vk):
    _send(vk=vk)
    _send(vk=vk, flags=KEYEVENTF_KEYUP)


def type_char(ch):
    _send(scan=ord(ch), flags=KEYEVENTF_UNICODE)
    _send(scan=ord(ch), flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)


def desktop_name(handle):
    buf = ctypes.create_unicode_buffer(256)
    need = wt.DWORD()
    user32.GetUserObjectInformationW(handle, 2, buf, ctypes.sizeof(buf), ctypes.byref(need))  # 2 = UOI_NAME
    return buf.value


def unlock():
    h = user32.OpenInputDesktop(0, False, 0x10000000)  # GENERIC_ALL
    if not h:
        return False, "Cannot open the input desktop. Run the server with start_server.bat (as SYSTEM)."
    try:
        name = desktop_name(h)
        if name.lower() != "winlogon":
            return False, "PC is not locked right now (desktop: %s)." % name
        if not user32.SetThreadDesktop(h):
            return False, "SetThreadDesktop failed (error %d)." % ctypes.get_last_error()
        tap_vk(VK_SHIFT)          # dismiss the lock-screen cover / wake display
        time.sleep(1.5)
        for ch in PASSWORD:
            type_char(ch)
            time.sleep(0.03)
        tap_vk(VK_RETURN)
        return True, "Unlocking..."
    finally:
        user32.CloseDesktop(h)


# ---------- HTTP ----------
seen = {}  # signature -> time, prevents replay


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, text):
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._reply(200, "Phone Unlock server is running.")

    def do_POST(self):
        if self.path != "/unlock":
            return self._reply(404, "not found")
        t = self.headers.get("X-Time", "")
        sig = self.headers.get("X-Sig", "")
        try:
            ts = int(t)
        except ValueError:
            return self._reply(400, "bad time")
        now = time.time()
        for k in [k for k, v in seen.items() if now - v > 120]:
            del seen[k]
        expected = hmac.new(SECRET, t.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return self._reply(403, "wrong secret")
        if abs(now - ts) > 60:
            return self._reply(403, "clock difference too big (check phone/PC time)")
        if sig in seen:
            return self._reply(403, "replay")
        seen[sig] = now
        ok, msg = unlock()
        print(time.strftime("%H:%M:%S"), msg)
        self._reply(200 if ok else 409, msg)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    try:
        ips = socket.gethostbyname_ex(socket.gethostname())[2]
    except Exception:
        ips = []
    print("Phone Unlock server on port %d" % PORT)
    print("Use one of these IPs in the phone app:", ", ".join(ips) or "(run ipconfig)")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
