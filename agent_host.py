"""
Agent Host for Long River Agent System (v2 - FastAPI).
Supports WebSocket terminal streaming, cloning, and GEMINI.md editing.
"""

import os
import sys
import pty
import tty
import select
import termios
import struct
import fcntl
import json
import shutil
import asyncio
import threading
import uvicorn
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Configuration
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
PROJECT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else ".").absolute()
CENTRAL_SERVER = os.environ.get("CENTRAL_SERVER_URL", "http://127.0.0.1:8000")

app = FastAPI(title=f"Agent Host - {PROJECT_DIR.name}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global PTY state
master_fd = None
terminal_clients: List[WebSocket] = []
terminal_history = bytearray()
MAX_HISTORY = 100000 # 100KB buffer for history

class ClonePayload(BaseModel):
    new_name: str
    overwrite: bool = False

class GeminiPayload(BaseModel):
    content: str

class CardPayload(BaseModel):
    card: dict

@app.get("/card")
async def get_card():
    card_path = PROJECT_DIR / "AgentCard.json"
    if not card_path.exists():
        return {"card": {}}
    try:
        return {"card": json.loads(card_path.read_text())}
    except:
        return {"card": {}}

@app.put("/card")
async def put_card(payload: CardPayload):
    card_path = PROJECT_DIR / "AgentCard.json"
    card_path.write_text(json.dumps(payload.card, indent=2, ensure_ascii=False))
    # Sync the new card immediately to the central server
    asyncio.create_task(register_with_central(PROJECT_DIR.name, PORT))
    return {"status": "saved"}

def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def pty_read_thread():
    global master_fd
    try:
        while master_fd is not None:
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    
                    # Mirror to local console
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()

                    # Add to history
                    terminal_history.extend(data)
                    if len(terminal_history) > MAX_HISTORY:
                        del terminal_history[:len(terminal_history) - MAX_HISTORY]

                    # Broadcast to all connected websockets as bytes
                    asyncio.run_coroutine_threadsafe(broadcast_terminal(data), loop)
                except OSError:
                    break
    except Exception as e:
        print(f"[Host] PTY read thread error: {e}")
    finally:
        if master_fd:
            try:
                os.close(master_fd)
            except:
                pass
            master_fd = None
        print("[Host] PTY closed, read thread exiting")

async def broadcast_terminal(data: bytes):
    for client in terminal_clients:
        try:
            await client.send_bytes(data)
        except:
            pass

child_pid = None

@app.on_event("startup")
async def startup_event():
    global master_fd, loop, child_pid
    loop = asyncio.get_event_loop()
    
    agent_name = PROJECT_DIR.name
    pid, master_fd = pty.fork()
    
    if pid == 0: # Child
        try:
            os.setsid() # Create a new process group for the child
        except:
            pass
        os.environ["GEMINI_PROJECT_DIR"] = str(PROJECT_DIR)
        os.environ["CENTRAL_SERVER_URL"] = CENTRAL_SERVER
        os.environ["LANG"] = "en_US.UTF-8"
        os.environ["LC_ALL"] = "en_US.UTF-8"
        os.environ["TERM"] = "xterm-256color"
        os.environ["COLORTERM"] = "truecolor"
        os.chdir(PROJECT_DIR)
        
        # Run gemini and then exec bash so the terminal stays alive
        bash_cmd = "if command -v gemini >/dev/null 2>&1; then gemini --yolo; else echo 'gemini CLI not found, dropping to bash...'; fi; exec bash"
        os.execvp("bash", ["bash", "-c", bash_cmd])
    else: # Parent
        child_pid = pid
        # Register with central server
        asyncio.create_task(register_with_central(agent_name, PORT))
        # Initial PTY size
        set_winsize(master_fd, 24, 80)
        # Start PTY reader thread
        threading.Thread(target=pty_read_thread, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    global master_fd, child_pid
    print(f"\n[Host] Shutting down agent {PROJECT_DIR.name}...")
    if child_pid:
        try:
            import signal
            # Kill the entire process group started by the child
            os.killpg(child_pid, signal.SIGTERM)
            print(f"[Host] Terminated child process group {child_pid}")
        except Exception as e:
            print(f"[Host] Error terminating child: {e}")
    
    if master_fd:
        try:
            os.close(master_fd)
        except:
            pass
        master_fd = None

async def register_with_central(name, port):
    # Wait a bit for central server to be ready
    await asyncio.sleep(1)
    card_path = PROJECT_DIR / "AgentCard.json"
    card = {}
    if card_path.exists():
        try:
            card = json.loads(card_path.read_text())
        except: pass
    
    payload = {"name": name, "host": "127.0.0.1", "port": port, "card": card}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{CENTRAL_SERVER}/register", json=payload, timeout=5)
            print(f"\n[Host] Registered {name} with Central Server at {CENTRAL_SERVER}")
    except Exception as e:
        print(f"\n[Host] Failed to register with Central: {e}")

@app.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    terminal_clients.append(websocket)
    
    # Send history first
    if terminal_history:
        await websocket.send_bytes(bytes(terminal_history))
        
    try:
        while True:
            # We now handle both string (keyboard/resize) and binary
            msg = await websocket.receive()
            
            if "text" in msg:
                data = msg["text"]
                try:
                    # Check if it's a JSON command (like resize)
                    if data.startswith("{") and data.endswith("}"):
                        cmd = json.loads(data)
                        if cmd.get("type") == "resize":
                            cols = cmd.get("cols", 80)
                            rows = cmd.get("rows", 24)
                            if master_fd:
                                set_winsize(master_fd, rows, cols)
                            continue
                except:
                    pass
                
                # Default to raw input
                if master_fd:
                    os.write(master_fd, data.encode())
            elif "bytes" in msg:
                if master_fd:
                    os.write(master_fd, msg["bytes"])
                    
    except WebSocketDisconnect:
        terminal_clients.remove(websocket)

async def smart_pty_write(text: str):
    global master_fd
    if not master_fd:
        return
        
    # Check for queued messages in recent history
    recent = terminal_history[-1000:].decode('utf-8', 'ignore')
    is_queued = "Queued (press ↑ to edit):" in recent
    
    if not is_queued:
        # Scenario 1: No queue - ESC then message
        os.write(master_fd, b"\x1b") # ESC
        await asyncio.sleep(0.1) # 100ms
        os.write(master_fd, text.encode())
        await asyncio.sleep(0.1)
        os.write(master_fd, b"\r") # Submission
    else:
        # Scenario 2: Queued - message then ESC
        os.write(master_fd, text.encode())
        await asyncio.sleep(0.1)
        os.write(master_fd, b"\x1b") # ESC
        await asyncio.sleep(0.1)
        os.write(master_fd, b"\r")

@app.post("/receive")
async def receive_mail(request: Request):
    data = await request.json()
    sender = data.get("from", "unknown")
    content = data.get("content", "")
    files = data.get("files", [])
    now_dt = datetime.now()
    now_display = now_dt.strftime("%m/%d %H:%M:%S")

    if not files:
        # Scenario 1: Direct Text Message (No files)
        # Just notify the terminal directly
        wake_msg = f"\n[MESSAGE] {now_display} {sender}: {content}"
        asyncio.create_task(smart_pty_write(wake_msg))
    else:
        # Scenario 2: Mail with Attachments
        mail_base = PROJECT_DIR / "mail"
        mail_base.mkdir(parents=True, exist_ok=True)
        timestamp_dir = now_dt.strftime("%m%d_%H%M%S")
        dir_name = f"{sender}_{timestamp_dir}"

        target_dir = mail_base / dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save message metadata
        msg_info = {
            "from": sender,
            "content": content,
            "timestamp": data.get("timestamp"),
            "message_id": data.get("message_id")
        }
        (target_dir / "message.json").write_text(json.dumps(msg_info, indent=2, ensure_ascii=False))

        # Copy forwarded files
        for f_path in files:
            src = Path(f_path)
            if src.exists():
                dst = target_dir / src.name
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        # Notify terminal about the mail
        wake_msg = f"\n[MAIL] {now_display} 来自 {sender} 的新消息（含附件）。内容已存入 mail/{dir_name}/。"
        asyncio.create_task(smart_pty_write(wake_msg))
    
    return {"status": "received"}

@app.post("/clone")
async def clone_agent(payload: ClonePayload):
    new_name = payload.new_name
    parent_dir = PROJECT_DIR.parent
    new_dir = parent_dir / new_name
    
    if new_dir.exists() and not payload.overwrite:
        raise HTTPException(status_code=400, detail="Agent already exists")
    
    if new_dir.exists():
        shutil.rmtree(new_dir)
        
    # Copy excluding some runtime dirs if they exist
    def ignore_patterns(path, names):
        return {n for n in names if n in {".git", "__pycache__", "mail", "checkpoint"}}

    shutil.copytree(PROJECT_DIR, new_dir, ignore=ignore_patterns)
    
    # Start the new agent host in a new process (or just return instructions)
    # For this prototype, we'll suggest the user start it or we can try os.system
    # In a real system, we'd have a process manager.
    # Here we'll just return success.
    return {"status": "cloned", "new_path": str(new_dir)}

@app.get("/gemini")
async def get_gemini():
    gemini_path = PROJECT_DIR / "GEMINI.md"
    if not gemini_path.exists():
        return {"content": ""}
    return {"content": gemini_path.read_text()}

@app.put("/gemini")
async def put_gemini(payload: GeminiPayload):
    gemini_path = PROJECT_DIR / "GEMINI.md"
    gemini_path.write_text(payload.content)
    
    # Trigger native /memory reload using smart injection
    asyncio.create_task(smart_pty_write("/memory reload"))
            
    return {"status": "saved"}

@app.get("/admin/agents/{agent_name}/card")
async def get_card():
    card_path = PROJECT_DIR / "AgentCard.json"
    if not card_path.exists():
        return {"card": {}}
    return {"card": json.loads(card_path.read_text())}

@app.put("/admin/agents/{agent_name}/card")
async def put_card_admin(agent_name: str, payload: dict):
    card_path = PROJECT_DIR / "AgentCard.json"
    card_path.write_text(json.dumps(payload, indent=2))
    asyncio.create_task(register_with_central(PROJECT_DIR.name, PORT))
    return {"status": "saved"}

if __name__ == "__main__":
    import select
    uvicorn.run(app, host="0.0.0.0", port=PORT)
