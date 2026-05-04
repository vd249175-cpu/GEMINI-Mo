import sys
import json
import os
import urllib.request
import re

def log(msg):
    sys.stderr.write(f"[sync-context] {msg}\n")

def find_project_root():
    if 'GEMINI_PROJECT_DIR' in os.environ:
        return os.environ['GEMINI_PROJECT_DIR']
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, '.gemini')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    return os.getcwd()

def fetch_online_agents():
    central_url = os.environ.get("CENTRAL_SERVER_URL", "http://127.0.0.1:8000")
    try:
        with urllib.request.urlopen(f"{central_url}/agents", timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data.get("agents", {})
    except Exception as e:
        log(f"Warning: Could not fetch peer agents: {e}")
        return {}

def run_hook():
    try:
        if sys.stdin.isatty(): return
        input_data = json.loads(sys.stdin.read())
        llm_request = input_data.get("llm_request")
        if not llm_request:
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        messages = llm_request.get("messages", [])
        
        # 1. Fetch and inject Peer Agent Cards
        agents_registry = fetch_online_agents()
        my_name = os.path.basename(find_project_root())
        
        peer_info = "\n\n### 👥 Online Peer Agents Registry:\n"
        if not agents_registry or len(agents_registry) <= 1:
            peer_info += "_No other agents are currently online._\n"
        else:
            for name, info in agents_registry.items():
                if name == my_name: continue
                card = info.get("card", {})
                peer_info += f"\n#### Agent: {name}\n"
                peer_info += f"- **Description**: {card.get('description', 'N/A')}\n"
                peer_info += f"- **Capabilities**: {', '.join(card.get('capabilities', []))}\n"
        
        # 2. Process Inbox
        inbox_path = ".gemini/inbox.json"
        inbox_messages = []
        if os.path.exists(inbox_path):
            try:
                with open(inbox_path, 'r') as f:
                    inbox_messages = json.load(f)
                os.remove(inbox_path)
            except Exception as e:
                log(f"Error processing inbox: {e}")

        mail_info = ""
        if inbox_messages:
            mail_info = "\n\n### 📥 New Incoming Messages:\n"
            for m in inbox_messages:
                mail_info += f"\n#### From: {m.get('from')}\n{m.get('content')}\n"

        # 3. Surgical Injection into System Instruction
        # Find or create a system message at the start
        system_msg_idx = -1
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                system_msg_idx = i
                break
        
        injection_content = f"\n\n--- Unified Discovery & Mail ---\n{peer_info}{mail_info}\n--- End Discovery & Mail ---\n"
        
        if system_msg_idx != -1:
            # Replace previous injection block if it exists, or append
            content = messages[system_msg_idx].get("content", "")
            pattern = r"\n\n--- Unified Discovery & Mail ---.*?--- End Discovery & Mail ---\n"
            if re.search(pattern, content, re.DOTALL):
                messages[system_msg_idx]["content"] = re.sub(pattern, injection_content, content, flags=re.DOTALL)
                log("Updated existing discovery/mail block in system message.")
            else:
                messages[system_msg_idx]["content"] += injection_content
                log("Appended discovery/mail block to system message.")
        else:
            # Create a new system message
            messages.insert(0, {
                "role": "system",
                "content": "You are part of a multi-agent system." + injection_content
            })
            log("Inserted new system message for discovery/mail.")

        llm_request["messages"] = messages
        print(json.dumps({
            "decision": "allow",
            "continue": True,
            "hookSpecificOutput": {"llm_request": llm_request}
        }))
    except Exception as e:
        log(f"Critical error: {str(e)}")
        print(json.dumps({"decision": "allow", "continue": True}))

if __name__ == "__main__":
    run_hook()
