import os
import sys
import pty
import tty
import select
import threading
import json
import http.server
import socketserver
import termios
import urllib.request
import struct
import fcntl
from pathlib import Path

# Configuration
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
PROJECT_DIR = sys.argv[2] if len(sys.argv) > 2 else "."
CENTRAL_SERVER = "http://127.0.0.1:8000"

INBOX_PATH = os.path.join(PROJECT_DIR, ".gemini/inbox.json")

class MessageHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/receive':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                inbox = []
                if os.path.exists(INBOX_PATH):
                    with open(INBOX_PATH, 'r') as f:
                        inbox = json.load(f)
                inbox.append(data)
                with open(INBOX_PATH, 'w') as f:
                    json.dump(inbox, f, indent=2)
                
                # Wake up Gemini CLI by injecting a newline
                os.write(self.server.master_fd, b"\n")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "received"}).encode())
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args): pass

class ServerThread(threading.Thread):
    def __init__(self, port, master_fd):
        threading.Thread.__init__(self)
        self.port = port
        self.master_fd = master_fd
        self.daemon = True

    def run(self):
        handler = MessageHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", self.port), handler) as httpd:
            httpd.server = self
            httpd.master_fd = self.master_fd
            httpd.serve_forever()

def register_with_central(name, port):
    card_path = os.path.join(PROJECT_DIR, "AgentCard.json")
    card = {}
    if os.path.exists(card_path):
        with open(card_path, 'r') as f:
            card = json.load(f)
    
    payload = {"name": name, "host": "127.0.0.1", "port": port, "card": card}
    try:
        req = urllib.request.Request(f"{CENTRAL_SERVER}/register", data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception: pass

def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def run_pty():
    agent_name = os.path.basename(os.path.abspath(PROJECT_DIR))
    old_tty = termios.tcgetattr(sys.stdin)
    pid, master_fd = pty.fork()
    
    if pid == 0: # Child
        os.environ["GEMINI_PROJECT_DIR"] = str(Path(PROJECT_DIR).absolute())
        os.environ["CENTRAL_SERVER_URL"] = CENTRAL_SERVER
        os.chdir(PROJECT_DIR)
        os.execvp("gemini", ["gemini"])
    else: # Parent
        if os.path.exists(INBOX_PATH): os.remove(INBOX_PATH)
        server = ServerThread(PORT, master_fd)
        server.start()
        register_with_central(agent_name, PORT)
        
        # Sync initial window size
        rows, cols = struct.unpack('HH', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HH', 0, 0)))
        set_winsize(master_fd, rows, cols)
        
        tty.setraw(sys.stdin.fileno())
        try:
            while True:
                r, w, e = select.select([sys.stdin, master_fd], [], [])
                if sys.stdin in r:
                    data = os.read(sys.stdin.fileno(), 4096)
                    if not data: break
                    os.write(master_fd, data)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data: break
                        os.write(sys.stdout.fileno(), data)
                        sys.stdout.flush()
                    except OSError: break
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            print("\n[Host] Session ended.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 agent_host.py <port> <directory>")
        sys.exit(1)
    run_pty()
