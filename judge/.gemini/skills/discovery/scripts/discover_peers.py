import sys
import json
import os
import urllib.request

def log(msg):
    sys.stderr.write(f"[discover-peers] {msg}\n")
    sys.stderr.flush()

def main():
    central_url = os.environ.get("CENTRAL_SERVER_URL", "http://127.0.0.1:8000")
    project_dir = os.environ.get("GEMINI_PROJECT_DIR", "")
    my_name = os.path.basename(project_dir.rstrip("/")) if project_dir else "unknown"

    try:
        # Only fetch peers that share a communication space with me
        url = f"{central_url}/agent/{my_name}/peers"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            peers = data.get("peers", [])
            
            print(f"--- 📡 Discovered Peers (Shared Spaces) ---")
            if not peers:
                print("No peers discovered. You might not be in any shared Spaces.")
            else:
                for peer in peers:
                    name = peer.get("name")
                    status = peer.get("status")
                    card = peer.get("card", {})
                    desc = card.get("description", "No description")
                    
                    status_icon = "🟢" if status == "online" else "⚪"
                    print(f"{status_icon} {name} ({status})")
                    print(f"   Description: {desc}")
            print("-------------------------------------------")
            
    except Exception as e:
        log(f"Error fetching peers: {e}")
        print(f"❌ Failed to connect to Central Server at {central_url}")

if __name__ == "__main__":
    main()
