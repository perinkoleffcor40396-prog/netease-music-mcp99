"""Vercel adapter for the upstream NetEase Music MCP server."""
import os
import sys

UPSTREAM_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "server", "mcp-server")
)
if UPSTREAM_DIR not in sys.path:
    sys.path.insert(0, UPSTREAM_DIR)

from server import MCPHandler  # noqa: E402


class handler(MCPHandler):
    """Expose the upstream MCP HTTP handler as a Vercel Python Function."""

    def do_GET(self):
        if self.path.rstrip("/") in ("/mcp", "/api/mcp"):
            self._json_response(
                {"error": "GET is not supported; use POST for MCP requests."},
                405,
            )
            return
        super().do_GET()
