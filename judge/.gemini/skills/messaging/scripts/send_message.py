import sys
import json
import os
import uuid
import urllib.request
import argparse


def log(msg):
    sys.stderr.write(f"[send-message] {msg}\n")
    sys.stderr.flush()


def main():
    parser = argparse.ArgumentParser(description="Send a message to another agent via the Central Server.")
    parser.add_argument("--to", required=True, help="Target agent name (e.g. 'judge', 'worker')")
    parser.add_argument("--content", required=True, help="Message body")
    parser.add_argument("--files", nargs="*", help="Paths to files or folders to forward")
    args = parser.parse_args()

    central_url = os.environ.get("CENTRAL_SERVER_URL", "http://127.0.0.1:8000")

    # Derive sender name
    project_dir = os.environ.get("GEMINI_PROJECT_DIR", "")
    if not project_dir:
        # scripts/ → messaging/ → skills/ → .gemini/ → project_root/
        # Need 5 dirnames to reach project_root from scripts/send_message.py
        project_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )
        )

    my_id = os.path.basename(project_dir.rstrip("/"))
    my_display_name = my_id
    
    # Try to read display name from AgentCard.json
    card_path = os.path.join(project_dir, "AgentCard.json")
    if os.path.exists(card_path):
        try:
            with open(card_path, "r", encoding="utf-8") as f:
                card = json.load(f)
                if card.get("name"):
                    my_display_name = card["name"]
        except Exception as e:
            log(f"Warning: Failed to read AgentCard.json: {e}")

    # Support multiple recipients (comma-separated or list-like string)
    targets = [t.strip() for t in args.to.replace("[", "").replace("]", "").split(",") if t.strip()]

    resolved_files = []
    if args.files:
        for f_path in args.files:
            abs_path = os.path.abspath(f_path)
            if os.path.exists(abs_path):
                resolved_files.append(abs_path)
            else:
                log(f"Warning: File not found: {f_path}")

    for target in targets:
        msg_id = uuid.uuid4().hex[:12]
        payload = {
            "message_id": msg_id,
            "from": my_id,
            "sender_name": my_display_name,
            "to": target,
            "content": args.content,
            "files": resolved_files,
            "hops": 0,
        }

        log(f"Sending from '{my_display_name}' to '{target}' (msg_id={msg_id}) with {len(resolved_files)} files via {central_url}")

        try:
            req = urllib.request.Request(
                f"{central_url}/send",
                data=json.dumps(payload, ensure_ascii=False).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
                status = result.get("status", "unknown")
                print(f"✅ Message sent to '{target}'. Status: {status} (msg_id={msg_id})")
        except Exception as e:
            log(f"Error sending message to '{target}': {e}")
            # Continue to next target even if one fails


if __name__ == "__main__":
    main()
