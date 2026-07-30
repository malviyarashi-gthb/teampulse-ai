"""
server.py - Clean Zero-Dependency Python HTTP Server for TeamPulse
Serves both REST API endpoints and the Frontend static files.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import mimetypes
import database
import agent

PORT = int(os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT", os.environ.get("PORT", 8080)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

class TeamPulseHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200, "text/plain")

    def _send_json(self, data, status_code=200):
        self._set_headers(status_code, "application/json")
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. API: Get all users
        if path == "/api/users":
            users = database.get_all_users()
            self._send_json(users)
            return

        # 2. API: Manager overview
        if path.startswith("/api/manager/") and path.endswith("/overview"):
            parts = path.strip("/").split("/")
            manager_ldap = parts[2] if len(parts) >= 3 else "malviyarashi"
            team = database.get_latest_team_status(manager_ldap)
            self._send_json({
                "manager_ldap": manager_ldap,
                "team_count": len(team),
                "team": team
            })
            return

        # 3. API: User history
        if path.startswith("/api/user/") and path.endswith("/history"):
            parts = path.strip("/").split("/")
            user_ldap = parts[2] if len(parts) >= 3 else ""
            history = database.get_user_history(user_ldap)
            self._send_json({"user_ldap": user_ldap, "history": history})
            return

        # 4. Static UI Files Serving
        file_path = None
        if path in ["/", "", "/index.html"]:
            file_path = os.path.join(STATIC_DIR, "index.html")
        else:
            rel = path.lstrip("/")
            file_path = os.path.join(STATIC_DIR, rel)
            if not os.path.exists(file_path):
                file_path = os.path.join(STATIC_DIR, "index.html")

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "text/html"
            self._set_headers(200, mime_type)
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"File not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/checkin":
            checkin_id = database.add_checkin(data)
            self._send_json({
                "success": True,
                "message": "Status update and pulse check submitted successfully!",
                "checkin_id": checkin_id
            })
            return

        elif path == "/api/agent/chat":
            manager_ldap = data.get("manager_ldap", "malviyarashi")
            message = data.get("message", "")
            response = agent.run_agent(message, manager_ldap)
            self._send_json(response)
            return

        elif path == "/api/team/add-member":
            ldap = data.get("ldap", "").strip()
            name = data.get("name", "").strip()
            title = data.get("title", "Software Engineer").strip()
            role = data.get("role", "reportee").strip()
            manager_ldap = data.get("manager_ldap", "malviyarashi").strip()
            if ldap and name:
                database.upsert_user(ldap, name, role, title, manager_ldap)
                self._send_json({"success": True, "message": f"Team member {name} added!"})
            else:
                self._send_json({"success": False, "error": "LDAP and Name required"}, 400)
            return

        elif path == "/api/sync-moma":
            manager_ldap = data.get("manager_ldap", "malviyarashi")
            reportees = database.get_reportees_for_manager(manager_ldap)
            self._send_json({
                "status": "synced",
                "source": "Moma TeamGraph & HR API Bridge",
                "manager": manager_ldap,
                "synced_reportees_count": len(reportees),
                "synced_reportees": [r["ldap"] for r in reportees]
            })
            return

        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

def run():
    database.init_db()
    print(f"🚀 TeamPulse Server running at http://localhost:{PORT}")
    print(f"👉 Manager Dashboard & Team Check-In available at http://localhost:{PORT}")
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(("0.0.0.0", PORT), TeamPulseHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
