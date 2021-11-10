#!/usr/bin/env python3

"""
A local server.
Hosts a built API on localhost:8000 and sets up CORS.
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="dist", **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


host = sys.argv[1] if len(sys.argv) > 2 else "0.0.0.0"
port = int(sys.argv[len(sys.argv) - 1]) if len(sys.argv) > 1 else 8000

print(f"Listening on {host}:{port}")
HTTPServer((host, port), RequestHandler).serve_forever()
