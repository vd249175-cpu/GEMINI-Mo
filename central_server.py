import http.server
import socketserver
import json
import threading
import sys
from datetime import datetime

PORT = 8000
agents = {} # name -> {host, port, card, last_seen}
messages_log = []

class CentralHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        if self.path == '/register':
            name = data.get("name")
            agents[name] = {
                "host": data.get("host"),
                "port": data.get("port"),
                "card": data.get("card"),
                "last_seen": datetime.now().isoformat()
            }
            print(f"[Central] Registered agent: {name} at {data.get('host')}:{data.get('port')}")
            self._send_json({"status": "ok", "agents": list(agents.keys())})

        elif self.path == '/send':
            sender = data.get("from")
            target = data.get("to")
            content = data.get("content")
            
            if target in agents:
                target_info = agents[target]
                try:
                    import urllib.request
                    url = f"http://{target_info['host']}:{target_info['port']}/receive"
                    req = urllib.request.Request(
                        url, 
                        data=json.dumps(data).encode(),
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        res = json.loads(resp.read().decode())
                        print(f"[Central] Routed message from {sender} to {target}: {res.get('status')}")
                        self._send_json({"status": "delivered"})
                except Exception as e:
                    print(f"[Central] Failed to route message to {target}: {e}")
                    self.send_error(502, f"Target agent unreachable: {e}")
            else:
                self.send_error(404, f"Target agent {target} not found")

    def do_GET(self):
        if self.path == '/agents':
            self._send_json({"agents": agents})
        else:
            self.send_error(404)

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Optional: logging
        pass

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CentralHandler) as httpd:
        print(f"[Central Server] Running on port {PORT}...")
        httpd.serve_forever()
