import sys
import json
import os
import urllib.request
import argparse

def log(msg):
    sys.stderr.write(f"[send-message] {msg}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()

    central_server_url = os.environ.get("CENTRAL_SERVER_URL", "http://127.0.0.1:8000")
    # Derive my name from the directory or environment
    my_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    
    payload = {
        "from": my_name,
        "to": args.to,
        "content": args.content,
        "type": "message"
    }
    
    log(f"Sending message to {args.to} via {central_server_url}...")
    
    try:
        req = urllib.request.Request(
            f"{central_server_url}/send",
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            print(f"Message delivered to {args.to}. Status: {result.get('status')}")
    except Exception as e:
        log(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
