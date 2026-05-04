"""
Central Message Broker for Long River Agent System (v2 - FastAPI).
Supports discovery via Spaces and Agent Replication.
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uuid
import httpx
import asyncio
import os
import subprocess
import signal
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Long River Central Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry: name -> {host, port, card, last_seen}
agents: Dict[str, Dict[str, Any]] = {}

# Process management: name -> subprocess.Popen
processes: Dict[str, Any] = {}
next_dynamic_port = 5005

# Per-agent mailbox: name -> [msg, ...]
mailboxes: Dict[str, List[Dict[str, Any]]] = {}

# Spaces for Venn-diagram discovery: {id, name, color, members: [name, ...]}
spaces: List[Dict[str, Any]] = [
    {"id": "space-default", "name": "Default Space", "color": "#2563eb", "members": []}
]

delivered_ids: set = set()
MAX_HOPS = 4

class RegisterPayload(BaseModel):
    name: str
    host: str = "127.0.0.1"
    port: int
    card: Optional[Dict[str, Any]] = None

class SendPayload(BaseModel):
    sender: str = Field(alias="from")
    target: str = Field(alias="to")
    content: str
    files: Optional[List[str]] = []
    hops: Optional[int] = 0
    message_id: Optional[str] = None
    type: Optional[str] = "message"

class SpaceUpdate(BaseModel):
    spaces: List[Dict[str, Any]]

class CreateAgentPayload(BaseModel):
    agent_name: str
    source_agent: str
    overwrite: bool = False

def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Long River Central Server is running",
        "agents_online": list(agents.keys()),
        "spaces_count": len(spaces)
    }

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/register")
async def register(payload: RegisterPayload):
    name = payload.name
    agents[name] = {
        "host": payload.host,
        "port": payload.port,
        "card": payload.card or {},
        "last_seen": _timestamp(),
    }
    if name not in mailboxes:
        mailboxes[name] = []
    else:
        for msg in mailboxes[name]:
            asyncio.create_task(_deliver_to_agent(name, msg))
        mailboxes[name].clear()
    
    # Auto-add to default space if new
    in_any = any(name in s["members"] for s in spaces)
    if not in_any:
        spaces[0]["members"].append(name)
        
    print(f"[Central] 📝 Registered: {name} @ {payload.host}:{payload.port}")
    return {"status": "ok", "agents": list(agents.keys())}

@app.get("/agents")
async def get_agents():
    return {"agents": agents}

@app.get("/admin/agents/available")
async def available_agents():
    online_names = set(agents.keys())
    agent_list = []
    
    # Scan filesystem for potential agent directories
    root_path = Path(".")
    ignored_dirs = {".git", "frontend", "logs", "__pycache__", ".venv", ".gemini", "workspace", "node_modules"}
    
    # Find all directories that aren't ignored
    discovered_names = []
    if root_path.exists():
        for path in root_path.iterdir():
            if path.is_dir() and not path.name.startswith(".") and path.name not in ignored_dirs:
                discovered_names.append(path.name)
    
    # Merge online data with disk data
    all_names = sorted(list(set(discovered_names) | online_names))
    
    for name in all_names:
        is_online = name in online_names
        status = "online" if is_online else "stopped"
        
        entry = {
            "agent_name": name,
            "status": status,
            "metadata": {},
            "communication_spaces": [s["id"] for s in spaces if name in s["members"]]
        }
        
        if is_online:
            entry["metadata"]["service_url"] = f"http://{agents[name]['host']}:{agents[name]['port']}"
            
        agent_list.append(entry)
        
    return {
        "agents": agent_list,
        "communication": {"spaces": spaces}
    }

@app.get("/admin/communication")
async def get_communication():
    return {"communication": {"spaces": spaces}}

@app.put("/admin/communication")
async def put_communication(payload: SpaceUpdate):
    global spaces
    spaces = payload.spaces
    return {"communication": {"spaces": spaces}}

@app.get("/admin/monitor")
async def monitor():
    # ... (existing monitor code)
    monitor_agents = []
    for name, info in agents.items():
        monitor_agents.append({
            "agent_name": name,
            "status": "online",
            "events": []
        })
    return {
        "agents": monitor_agents,
        "mailbox_counts": {name: len(msgs) for name, msgs in mailboxes.items()},
        "recent_mail": []
    }

@app.get("/agent/{agent_name}/peers")
async def get_agent_peers(agent_name: str):
    # Find spaces this agent belongs to
    my_spaces = [s["id"] for s in spaces if agent_name in s["members"]]
    
    peers_set = set()
    for s in spaces:
        if s["id"] in my_spaces:
            for member in s["members"]:
                if member != agent_name:
                    peers_set.add(member)
    
    peer_list = []
    for peer_name in sorted(list(peers_set)):
        is_online = peer_name in agents
        peer_list.append({
            "name": peer_name,
            "status": "online" if is_online else "stopped",
            "card": agents[peer_name]["card"] if is_online else {}
        })
        
    return {"peers": peer_list}

@app.post("/send")
async def handle_send(payload: SendPayload):
    sender = payload.sender
    target = payload.target
    content = payload.content
    hops = payload.hops + 1
    msg_id = payload.message_id or uuid.uuid4().hex[:12]

    if hops > MAX_HOPS:
        return {"status": "dropped", "reason": "hop_limit_exceeded"}

    msg = {
        "message_id": msg_id,
        "from": sender,
        "to": target,
        "content": content,
        "files": payload.files,
        "hops": hops,
        "timestamp": _timestamp(),
        "type": payload.type
    }

    if msg_id in delivered_ids:
        return {"status": "duplicate"}

    if target not in agents:
        if target not in mailboxes:
            mailboxes[target] = []
        mailboxes[target].append(msg)
        return {"status": "queued", "message_id": msg_id}

    delivered_ids.add(msg_id)
    
    # Async delivery
    asyncio.create_task(_deliver_to_agent(target, msg))
    return {"status": "delivered", "message_id": msg_id}

async def _deliver_to_agent(target_name: str, msg: dict):
    if target_name not in agents:
        return
    info = agents[target_name]
    url = f"http://{info['host']}:{info['port']}/receive"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=msg, timeout=5)
    except Exception as e:
        print(f"[Central] ❌ Delivery failed to {target_name}: {e}")

import socket

def get_free_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                port += 98

@app.post("/admin/agents/{agent_name}/start")
async def start_agent(agent_name: str):
    global next_dynamic_port
    if agent_name in agents:
        return {"status": "already_online", "agent_name": agent_name}
    
    agent_path = Path(agent_name)
    if not agent_path.exists() or not agent_path.is_dir():
        raise HTTPException(status_code=404, detail="Agent directory not found")
    
    port = get_free_port(next_dynamic_port)
    next_dynamic_port = port + 98
    
    cmd = ["uv", "run", "python", "agent_host.py", str(port), f"./{agent_name}"]
    try:
        # Start in a new process group so we can kill it later
        log_file = open(f"logs/{agent_name}_{port}.log", "w")
        proc = subprocess.Popen(
            cmd, 
            stdout=log_file, 
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        processes[agent_name] = proc
        print(f"[Central] 🚀 Started agent {agent_name} on port {port} (PID: {proc.pid})")
        
        # Wait for registration (opportunistic)
        for _ in range(10):
            await asyncio.sleep(0.5)
            if agent_name in agents:
                break
                
        return {"status": "starting", "agent_name": agent_name, "port": port}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/agents/{agent_name}/stop")
async def stop_agent(agent_name: str):
    if agent_name in processes:
        proc = processes[agent_name]
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            print(f"[Central] 🛑 Stopped agent {agent_name} (PID: {proc.pid})")
        except:
            pass
        del processes[agent_name]
    
    if agent_name in agents:
        del agents[agent_name]
        
    return {"status": "stopped", "agent_name": agent_name}

@app.delete("/admin/agents/{agent_name}")
async def delete_agent(agent_name: str):
    if agent_name in processes:
        await stop_agent(agent_name)
    
    agent_path = Path(agent_name)
    if agent_path.exists() and agent_path.is_dir():
        import shutil
        # Use to_thread to avoid blocking event loop
        await asyncio.to_thread(shutil.rmtree, agent_path)
        print(f"[Central] 🗑️ Deleted agent {agent_name}")
    
    return {"status": "deleted", "agent_name": agent_name}

import shutil

@app.post("/admin/agents/create")
async def create_agent(payload: CreateAgentPayload):
    source = payload.source_agent
    new_name = payload.agent_name
    
    source_path = Path(source)
    new_path = Path(new_name)
    
    if not source_path.exists() or not source_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Source agent {source} directory not found")
    
    if new_path.exists() and not payload.overwrite:
        raise HTTPException(status_code=400, detail="Target agent directory already exists")
    
    try:
        if new_path.exists():
            shutil.rmtree(new_path)
            
        def ignore_patterns(path, names):
            return {n for n in names if n in {".git", "__pycache__", "mail", "checkpoint", "logs", "node_modules", ".venv", ".DS_Store", "workspace", "handswriter-image-gen"}}

        # Perform copy directly from central server (which is in the root)
        # Use asyncio.to_thread to avoid blocking the event loop
        await asyncio.to_thread(shutil.copytree, source_path, new_path, ignore=ignore_patterns)
        
        print(f"[Central] 👯 Cloned {source} -> {new_name}")
        return {"status": "cloned", "new_name": new_name, "path": str(new_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
