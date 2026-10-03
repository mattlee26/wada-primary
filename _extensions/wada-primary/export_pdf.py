#!/usr/bin/env python3
"""Export a rendered Wada Primary deck to PDF with headless Chrome (no other dependencies).

    python3 _extensions/wada-primary/export_pdf.py template.html            # -> template.pdf
    python3 _extensions/wada-primary/export_pdf.py template.html talk.pdf
    python3 _extensions/wada-primary/export_pdf.py http://localhost:4200/   # a served deck

Opens the deck in reveal.js print mode (?print-pdf), waits until every slide is laid
out on its own page, then prints at the deck's 16:9 page size with backgrounds.
Needs Google Chrome, Chromium or Microsoft Edge; set CHROME=/path/to/browser if it
is not found. Fonts load from the web, so stay online while exporting.
"""

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]


def find_browser():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for path in CANDIDATES:
        if Path(path).exists():
            return path
    for name in NAMES:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Chrome, Chromium or Edge not found; set CHROME=/path/to/browser")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DevTools:
    """Just enough of the Chrome DevTools protocol (a WebSocket client) to print."""

    def __init__(self, ws_url):
        host_port, path = ws_url[len("ws://"):].split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError("browser closed the connection")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _send(self, payload):
        data = json.dumps(payload).encode()
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(data))
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", len(data))
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _receive(self):
        message = b""
        while True:
            first, second = self._read(2)
            n = second & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            message += self._read(n)
            if first & 0x80:
                return json.loads(message)

    def call(self, method, **params):
        self.next_id += 1
        self._send({"id": self.next_id, "method": method, "params": params})
        while True:
            reply = self._receive()
            if reply.get("id") == self.next_id:
                if "error" in reply:
                    raise RuntimeError(reply["error"])
                return reply["result"]

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        return result["result"].get("value")


def deck_url(target):
    if target.startswith(("http://", "https://", "file://")):
        url = target
    else:
        path = Path(target).resolve()
        if not path.exists():
            sys.exit(f"{target} not found; render the deck first (quarto render)")
        url = path.as_uri()
    url = url.split("#")[0]
    return url + ("&" if "?" in url else "?") + "print-pdf"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    target = sys.argv[1]
    out = Path(sys.argv[2] if len(sys.argv) > 2 else
               (Path(target).with_suffix(".pdf").name if not target.startswith("http") else "slides.pdf"))

    port = free_port()
    profile = tempfile.mkdtemp(prefix="wada-primary-pdf-")
    browser = subprocess.Popen(
        [find_browser(), "--headless=new", "--disable-gpu", "--no-first-run", "--allow-file-access-from-files",
         f"--remote-debugging-port={port}", f"--user-data-dir={profile}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = next(p for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.1)
        else:
            sys.exit("could not connect to the browser")

        tools = DevTools(page["webSocketDebuggerUrl"])
        tools.call("Page.enable")
        tools.call("Page.navigate", url=deck_url(target))

        # Wait until reveal.js has put every slide on a page, then for fonts and images
        count, stable, deadline = 0, 0, time.time() + 60
        while time.time() < deadline:
            time.sleep(0.25)
            n = tools.evaluate("document.querySelectorAll('.pdf-page').length") or 0
            stable = stable + 1 if n and n == count else 0
            count = n
            if stable >= 4:
                break
        if not count:
            sys.exit("the deck never entered print layout; is it a reveal.js deck?")
        tools.evaluate("document.fonts.ready.then(() => true)")
        time.sleep(1)

        pdf = tools.call("Page.printToPDF", printBackground=True, preferCSSPageSize=True,
                         displayHeaderFooter=False, marginTop=0, marginBottom=0,
                         marginLeft=0, marginRight=0)
        out.write_bytes(base64.b64decode(pdf["data"]))
        print(f"{out} ({count} slides)")
    finally:
        browser.terminate()
        try:
            browser.wait(timeout=5)
        except subprocess.TimeoutExpired:
            browser.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
