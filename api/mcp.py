"""Vercel adapter for the upstream NetEase Music MCP server.

The upstream server keeps the NetEase API/tool implementation in server.py.
This adapter only provides a Vercel-compatible BaseHTTPRequestHandler and
reuses the upstream TOOLS and TOOL_DISPATCH registries.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

UPSTREAM_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "server", "mcp-server")
)
if UPSTREAM_DIR not in sys.path:
    sys.path.insert(0, UPSTREAM_DIR)

from server import TOOLS, TOOL_DISPATCH  # noqa: E402


class handler(BaseHTTPRequestHandler):
    """Expose the upstream MCP protocol as a Vercel Python Function."""

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # MCP itself uses POST. Keep a simple health response for browser checks.
        if self.path.rstrip("/") in ("/api/mcp", "/mcp"):
            self._json_response(
                {"status": "ok", "message": "NetEase Music MCP endpoint is online", "tools": len(TOOLS)},
                200,
            )
            return
        self._json_response({"error": "Not found"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw_body)
        except Exception as exc:
            self._json_response(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}},
                400,
            )
            return

        method = body.get("method", "")
        req_id = body.get("id")

        if method.startswith("notifications/") or req_id is None:
            self.send_response(204)
            self._cors()
            self.end_headers()
            return

        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "netease-music-mcp", "version": "3.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = body.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool_func = TOOL_DISPATCH.get(tool_name)
            if not tool_func:
                result = {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True,
                }
            else:
                try:
                    tool_result = tool_func(arguments)
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(tool_result, ensure_ascii=False),
                            }
                        ]
                    }
                except Exception as exc:
                    result = {
                        "content": [
                            {"type": "text", "text": json.dumps({"error": str(exc)}, ensure_ascii=False)}
                        ],
                        "isError": True,
                    }
        else:
            result = {"error": {"code": -32601, "message": f"Unknown method: {method}"}}

        self._json_response({"jsonrpc": "2.0", "id": req_id, "result": result})

    def log_message(self, format, *args):
        pass
