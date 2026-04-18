#!/usr/bin/env python3
"""Dummy Kelet API server for eval runs.

Mirrors the response contract of POST /api/projects/{project}/synthetics so the
kelet-integration skill can be exercised end-to-end without real credentials.

Contract source: kelet/server/app/routers/synthetics.py +
kelet/server/tests/test_synthetics_endpoint.py. Update this stub's response
strings when those change.

Branches (ordered):
  - Authorization missing or not "Bearer sk-kelet-*" -> 401 JSON
  - {project} == "not-a-real-project"                -> 404 JSON + hint
  - otherwise                                        -> 200 text/plain

Run: `python3 evals/dummy_server.py [--port 8765]`
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

SYNTHETICS_PATH = re.compile(r"^/api/projects/([^/]+)/synthetics/?$")
BAD_PROJECT = "not-a-real-project"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - match base signature
        del format
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else '?'}")

    def _reply(self, status, body, content_type):
        payload = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        match = SYNTHETICS_PATH.match(self.path)
        if not match:
            self._reply(404, '{"detail":"not found"}', "application/json")
            return

        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer sk-kelet-"):
            self._reply(401, '{"detail":"Not authenticated"}', "application/json")
            return

        project = match.group(1)
        if project == BAD_PROJECT:
            body = json.dumps({
                "detail": {
                    "error": "project_not_found",
                    "project": BAD_PROJECT,
                    "hint": "Create it first at console.kelet.ai \u2192 New Project, then re-run.",
                }
            })
            self._reply(404, body, "application/json")
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            ideas = json.loads(raw).get("ideas", []) if raw else []
        except json.JSONDecodeError:
            ideas = []
        count = len(ideas) if isinstance(ideas, list) else 0
        self._reply(
            200,
            f"created={count} updated=0 failed=0 deduped=false",
            "text/plain",
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dummy Kelet API listening on http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
