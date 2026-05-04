import sys
import json
import os
import urllib.request

def log(msg):
    sys.stderr.write(f"[notify-peer] {msg}\n")

def run_hook():
    try:
        # 1. Read input data from stdin
        if sys.stdin.isatty():
            return
            
        input_data = json.load(sys.stdin)
        
        # AfterAgent hook provides 'prompt_response'
        response_text = input_data.get("prompt_response", "")
        if not response_text:
            log("No response text found to send.")
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        # 2. Get target port from environment
        peer_port = os.environ.get("AGENT_PEER_PORT")
        if not peer_port:
            log("AGENT_PEER_PORT not set. Skipping notification.")
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        # 3. Construct message for the peer
        # We might want to wrap it in a specific instruction
        my_name = os.path.basename(os.getcwd())
        message_to_send = f"### Message from {my_name}:\n\n{response_text}"
        
        payload = {"content": message_to_send}
        
        # 4. Send to the peer host
        url = f"http://127.0.0.1:{peer_port}/message"
        log(f"Sending message to {url}...")
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                log(f"Notification status: {result.get('status')}")
        except Exception as e:
            log(f"Failed to notify peer: {e}")

        # 5. Continue normally
        print(json.dumps({"decision": "allow", "continue": True}))
        
    except Exception as e:
        log(f"Critical error: {e}")
        print(json.dumps({"decision": "allow", "continue": True}))

if __name__ == "__main__":
    run_hook()
