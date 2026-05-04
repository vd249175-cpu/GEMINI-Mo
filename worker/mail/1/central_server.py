"""
Central Message Broker for Gemini CLI Multi-Agent System.

Improvements over v1:
- Per-agent mailboxes with unique message IDs
- Round-trip (ping-pong) loop prevention via hop counter
- Message ACK to prevent re-delivery
- Proper /send injection to agent PTY host
"""

import http.server
import socketserver
import json
import uuid
import threading
import sys
from datetime import datetime

PORT = 8000

# Agent registry: name -> {host, port, card, last_seen}
agents: dict = {}

# Per-agent mailbox: name -> [msg, ...]
# Each msg: {message_id, from, to, content, hops, timestamp}
mailboxes: dict = {}

# Delivered message IDs (for dedup / ACK)
delivered_ids: set = set()

MAX_HOPS = 4  # Prevent infinite ping-pong; a round trip is 2 hops

lock = threading.Lock()


def _new_message_id() -> str:
    return uuid.uuid4().hex[:12]


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _deliver_to_agent(target_name: str, msg: dict) -> bool:
    """Forward msg to the target agent's HTTP host (which injects into PTY)."""
    if target_name not in agents:
        return False
    info = agents[target_name]
    try:
        import urllib.request
        url = f"http://{info['host']}:{info['port']}/receive"
        body = json.dumps(msg).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode())
            print(f"[Central] ✅ Delivered {msg['message_id']} from {msg['from']} → {target_name}: {res.get('status')}")
            return True
    except Exception as e:
        print(f"[Central] ❌ Failed to deliver to {target_name}: {e}")
        return False


class CentralHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._error(400, str(e))
            return

        if self.path == "/register":
            self._handle_register(data)
        elif self.path == "/send":
            self._handle_send(data)
        elif self.path == "/ack":
            self._handle_ack(data)
        else:
            self._error(404, "Unknown path")

    def do_GET(self):
        if self.path == "/agents":
            with lock:
                self._send_json({"agents": agents})
        elif self.path.startswith("/mailbox/"):
            agent_name = self.path.split("/mailbox/", 1)[1]
            with lock:
                msgs = mailboxes.get(agent_name, [])
            self._send_json({"messages": msgs, "count": len(msgs)})
        else:
            self._error(404, "Not found")

    # ------------------------------------------------------------------ #

    def _handle_register(self, data: dict):
        name = data.get("name", "").strip()
        if not name:
            self._error(400, "name required")
            return
        with lock:
            agents[name] = {
                "host": data.get("host", "127.0.0.1"),
                "port": data.get("port"),
                "card": data.get("card", {}),
                "last_seen": _timestamp(),
            }
            if name not in mailboxes:
                mailboxes[name] = []
        print(f"[Central] 📝 Registered: {name} @ {data.get('host')}:{data.get('port')}")
        self._send_json({"status": "ok", "agents": list(agents.keys())})

    def _handle_send(self, data: dict):
        sender = data.get("from", "unknown")
        target = data.get("to", "").strip()
        content = data.get("content", "")
        hops = int(data.get("hops", 0)) + 1  # increment hop counter

        if not target:
            self._error(400, "to field required")
            return

        if hops > MAX_HOPS:
            print(f"[Central] 🛑 Message from {sender} to {target} dropped: hop limit {MAX_HOPS} reached (loop prevention)")
            self._send_json({"status": "dropped", "reason": "hop_limit_exceeded", "hops": hops})
            return

        msg_id = data.get("message_id") or _new_message_id()
        msg = {
            "message_id": msg_id,
            "from": sender,
            "to": target,
            "content": content,
            "files": data.get("files", []),
            "hops": hops,
            "timestamp": _timestamp(),
        }

        with lock:
            if msg_id in delivered_ids:
                print(f"[Central] ⚠️  Duplicate message {msg_id} dropped")
                self._send_json({"status": "duplicate"})
                return

            if target not in agents:
                # Queue for later delivery when agent comes online
                if target not in mailboxes:
                    mailboxes[target] = []
                mailboxes[target].append(msg)
                print(f"[Central] 📥 Queued for offline agent {target}: {msg_id}")
                self._send_json({"status": "queued", "message_id": msg_id})
                return

            delivered_ids.add(msg_id)
            # Keep set bounded
            if len(delivered_ids) > 2000:
                # Remove oldest ~500
                for _ in range(500):
                    delivered_ids.pop()

        # Deliver outside lock to avoid blocking
        ok = _deliver_to_agent(target, msg)
        if ok:
            self._send_json({"status": "delivered", "message_id": msg_id, "hops": hops})
        else:
            with lock:
                if target not in mailboxes:
                    mailboxes[target] = []
                mailboxes[target].append(msg)
            self._send_json({"status": "queued_on_failure", "message_id": msg_id})

    def _handle_ack(self, data: dict):
        msg_id = data.get("message_id", "")
        with lock:
            delivered_ids.add(msg_id)
        self._send_json({"status": "acked", "message_id": msg_id})

    # ------------------------------------------------------------------ #

    def _send_json(self, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code: int, msg: str):
        self.send_error(code, msg)

    def log_message(self, format, *args):
        pass  # suppress default access log


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CentralHandler) as httpd:
        print(f"[Central Server] 🚀 Running on port {PORT}  (MAX_HOPS={MAX_HOPS})")
        httpd.serve_forever()
