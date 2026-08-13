#!/usr/bin/env python3
"""Local switch endpoint for the Now Playing kiosk Solari button."""
from __future__ import annotations

import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

MODE_FILE = os.environ.get("TIVOLI_MODE_FILE", "/home/volumio/.tivoli-display-mode")
PORT = int(os.environ.get("TIVOLI_SWITCHD_PORT", "4011"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"ok"):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_POST(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/solari", "/switch"):
            try:
                with open(MODE_FILE, "w") as handle:
                    handle.write("solari\n")
            except OSError:
                self._send(500, b"mode file")
                return
            subprocess.call(
                ["killall", "chromium-browser"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.call(
                ["killall", "chromium-browser-v7"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._send(200, b"solari")
            return
        if path in ("/", "/health"):
            self._send(200, b"ok")
            return
        self._send(404, b"no")

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
