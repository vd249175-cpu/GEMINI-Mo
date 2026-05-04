import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Bot,
  CheckCircle2,
  Copy,
  Database,
  FileText,
  Mail,
  MessageSquare,
  Network,
  Play,
  Plus,
  RefreshCw,
  Save,
  Square,
  Terminal as TerminalIcon,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import "./styles.css";

function shortId(prefix = "") {
  return `${prefix}${Math.random().toString(36).slice(2, 10)}`;
}

function edgeKey(left, right) {
  return [left, right].sort().join("::");
}

function buildEdges(spaces, agentNames) {
  const allowed = new Set(agentNames);
  const edgeMap = new Map();
  for (const space of spaces) {
    const members = (space.members || []).filter((name) => allowed.has(name));
    for (let i = 0; i < members.length; i += 1) {
      for (let j = i + 1; j < members.length; j += 1) {
        const key = edgeKey(members[i], members[j]);
        const existing = edgeMap.get(key) || { from: members[i], to: members[j], spaces: [] };
        existing.spaces.push(space.id);
        edgeMap.set(key, existing);
      }
    }
  }
  return [...edgeMap.values()];
}

function agentPosition(agent, index, positions) {
  const saved = positions?.[agent.agent_name];
  if (saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)) return saved;
  return { x: 120 + (index % 3) * 260, y: 120 + Math.floor(index / 3) * 170 };
}

function App() {
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("centralUrl") || "http://127.0.0.1:8000");
  const [agents, setAgents] = useState([]);
  const [communication, setCommunication] = useState({ spaces: [] });
  const [agentPositions, setAgentPositions] = useState({});
  const [selectedAgent, setSelectedAgent] = useState("");
  const [selectedSpaceId, setSelectedSpaceId] = useState("");
  const [activeTab, setActiveTab] = useState("graph");
  const [status, setStatus] = useState("Ready");
  const [online, setOnline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [geminiContent, setGeminiContent] = useState("");
  const [cardContent, setCardContent] = useState("{}");

  const [newSpaceName, setNewSpaceName] = useState("");
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(null);
  const [cloning, setCloning] = useState(null);
  const [graphGesture, setGraphGesture] = useState(null);

  const graphCanvasRef = useRef(null);
  const terminalRef = useRef(null);
  const terminalsMap = useRef({}); // Store { agentName: { term, fitAddon, socket } }
  const xtermRef = useRef(null);
  const socketRef = useRef(null);

  const spaces = useMemo(() => communication.spaces || [], [communication]);
  const agentNames = agents.map((agent) => agent.agent_name);
  const edges = useMemo(() => buildEdges(spaces, agentNames), [spaces, agentNames]);
  const selectedSummary = agents.find((agent) => agent.agent_name === selectedAgent);
  const selectedSpace = spaces.find((space) => space.id === selectedSpaceId) || spaces[0] || null;

  const api = async (path, options = {}) => {
    const root = baseUrl.replace(/\/$/, "");
    const response = await fetch(`${root}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  };

  const agentApi = async (path, options = {}) => {
    if (!selectedSummary?.metadata?.service_url) throw new Error("Agent service URL not found");
    const response = await fetch(`${selectedSummary.metadata.service_url}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  };

  const refreshAgents = async () => {
    try {
      const result = await api("/admin/agents/available");
      setAgents(result.agents || []);
      setCommunication(result.communication || { spaces: [] });
      setOnline(true);
      setStatus("Connected");
    } catch (error) {
      setOnline(false);
      setStatus(`Connection failed: ${error.message}`);
    }
  };

  useEffect(() => {
    localStorage.setItem("centralUrl", baseUrl);
    refreshAgents();
    const timer = setInterval(refreshAgents, 3000);
    return () => clearInterval(timer);
  }, [baseUrl]);

  // Terminal logic with persistence
  useEffect(() => {
    if (activeTab !== "terminal" || !selectedAgent || !selectedSummary?.metadata?.service_url) return;

    const agentName = selectedAgent;
    let entry = terminalsMap.current[agentName];

    if (!entry) {
      const term = new XTerm({
        theme: { background: "#000000" },
        cursorBlink: true,
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        fontSize: 14,
        convertEol: true,
      });
      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      
      const wsUrl = selectedSummary.metadata.service_url.replace(/^http/, "ws") + "/terminal";
      const socket = new WebSocket(wsUrl);
      socket.binaryType = "arraybuffer";

      socket.onmessage = (event) => {
        term.write(new Uint8Array(event.data));
        term.scrollToBottom();
      };

      term.onData((data) => {
        // FILTER: Prevent auto-DA response (ghost input)
        // \x1b[?1;2c is the typical response that causes the bug
        if (data === "\x1b[?1;2c" || data === "\x1b[?6c") {
          return;
        }
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(data);
        }
      });

      entry = { term, fitAddon, socket };
      terminalsMap.current[agentName] = entry;
    }

    // Attach to the current DOM ref
    const { term, fitAddon, socket } = entry;
    
    // CRUCIAL: Clear the container first to prevent multiple terminals stacking/overlapping
    if (terminalRef.current) {
      terminalRef.current.innerHTML = "";
      if (term.element) {
        // If already opened, just move the existing element
        terminalRef.current.appendChild(term.element);
      } else {
        // First time, use open()
        term.open(terminalRef.current);
      }
    }
    
    xtermRef.current = term;
    socketRef.current = socket;
    
    // Always call fit after attaching
    const handleResize = () => {
      if (!terminalRef.current) return;
      try {
        fitAddon.fit();
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
        }
      } catch (e) {}
    };

    term.focus(); // Ensure input focus

    if (socket.readyState === WebSocket.OPEN) {
      handleResize();
      term.refresh(0, term.rows - 1);
    } else {
      socket.onopen = () => {
        handleResize();
        term.refresh(0, term.rows - 1);
      };
    }

    window.addEventListener("resize", handleResize);
    const t1 = setTimeout(handleResize, 50);
    const t2 = setTimeout(handleResize, 300);
    const t3 = setTimeout(() => term.refresh(0, term.rows - 1), 400);

    return () => {
      // Don't dispose term/socket, just remove listener
      window.removeEventListener("resize", handleResize);
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [activeTab, selectedAgent, selectedSummary?.metadata?.service_url]);

  // Gemini and Card editor logic
  useEffect(() => {
    if (selectedAgent) {
      if (activeTab === "gemini") {
        agentApi("/gemini").then((res) => setGeminiContent(res.content || ""));
      } else if (activeTab === "card") {
        agentApi("/card").then((res) => setCardContent(JSON.stringify(res.card || {}, null, 2)));
      }
    }
  }, [activeTab, selectedAgent]);

  const saveGemini = async () => {
    setBusy(true);
    try {
      await agentApi("/gemini", { method: "PUT", body: JSON.stringify({ content: geminiContent }) });
      setStatus("GEMINI.md saved");
    } catch (error) {
      setStatus(`Save failed: ${error.message}`);
    }
    setBusy(false);
  };

  const saveCard = async () => {
    setBusy(true);
    try {
      const card = JSON.parse(cardContent);
      await agentApi("/card", { method: "PUT", body: JSON.stringify({ card }) });
      setStatus("AgentCard.json saved");
    } catch (error) {
      setStatus(`Save failed: ${error.message}`);
    }
    setBusy(false);
  };

  // Graph interaction
  const screenToGraph = (point) => ({ x: point.x - panOffset.x, y: point.y - panOffset.y });
  const graphPoint = (event) => {
    const rect = graphCanvasRef.current.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  };

  const startCanvasGesture = (event) => {
    if (event.button !== 0 || event.target.closest(".graph-agent")) return;
    setGraphGesture({
      mode: "pan",
      startX: event.clientX,
      startY: event.clientY,
      originX: panOffset.x,
      originY: panOffset.y,
    });
  };

  const moveCanvasGesture = (event) => {
    if (dragging) {
      const graph = screenToGraph(graphPoint(event));
      const nextPositions = {
        ...agentPositions,
        [dragging.agentName]: { x: Math.max(20, graph.x - dragging.dx), y: Math.max(20, graph.y - dragging.dy) },
      };
      setAgentPositions(nextPositions);
      return;
    }
    if (cloning) {
      const graph = screenToGraph(graphPoint(event));
      setCloning((prev) => ({ ...prev, currentX: graph.x, currentY: graph.y }));
      return;
    }
    if (graphGesture?.mode === "pan") {
      setPanOffset({
        x: graphGesture.originX + event.clientX - graphGesture.startX,
        y: graphGesture.originY + event.clientY - graphGesture.startY,
      });
    }
  };

  const startDrag = (event, agentName, position) => {
    event.stopPropagation();
    setSelectedAgent(agentName);
    const graph = screenToGraph(graphPoint(event));
    if (event.altKey || event.metaKey) {
      setCloning({ sourceName: agentName, startX: position.x, startY: position.y, currentX: graph.x, currentY: graph.y });
    } else {
      setDragging({ agentName, dx: graph.x - position.x, dy: graph.y - position.y });
    }
  };

  const finishGesture = async (event) => {
    if (cloning) {
      const newName = prompt("Enter name for the cloned agent:", `${cloning.sourceName}_copy`);
      if (newName) {
        setBusy(true);
        setStatus(`Cloning ${cloning.sourceName}...`);
        try {
          await api("/admin/agents/create", {
            method: "POST",
            body: JSON.stringify({ agent_name: newName, source_agent: cloning.sourceName }),
          });
          const graph = screenToGraph(graphPoint(event));
          setAgentPositions((prev) => ({ ...prev, [newName]: { x: graph.x, y: graph.y } }));
          refreshAgents();
          setStatus("Cloned successfully");
        } catch (error) {
          setStatus(`Clone failed: ${error.message}`);
        }
        setBusy(false);
      }
      setCloning(null);
    }
    setDragging(null);
    setGraphGesture(null);
  };

  const toggleSpaceMember = (agentName) => {
    if (!selectedSpace) return;
    const nextSpaces = spaces.map((s) => {
      if (s.id !== selectedSpace.id) return s;
      const members = new Set(s.members || []);
      if (members.has(agentName)) members.delete(agentName);
      else members.add(agentName);
      return { ...s, members: Array.from(members) };
    });
    api("/admin/communication", { method: "PUT", body: JSON.stringify({ spaces: nextSpaces }) }).then(refreshAgents);
  };

  const addSpace = () => {
    const name = prompt("New space name:");
    if (!name) return;
    const nextSpaces = [...spaces, { id: shortId("space-"), name, color: "#2563eb", members: [] }];
    api("/admin/communication", { method: "PUT", body: JSON.stringify({ spaces: nextSpaces }) }).then(refreshAgents);
  };

  const handleToggleService = async (agent) => {
    if (!agent) return;
    setBusy(true);
    const action = agent.status === "online" ? "stop" : "start";
    setStatus(`${action === "start" ? "Starting" : "Stopping"} ${agent.agent_name}...`);
    try {
      await api(`/admin/agents/${agent.agent_name}/${action}`, { method: "POST" });
      await refreshAgents();
      setStatus(`${agent.agent_name} ${action === "start" ? "started" : "stopped"}`);
    } catch (error) {
      setStatus(`Action failed: ${error.message}`);
    }
    setBusy(false);
  };

  const handleClone = async (sourceName) => {
    const newName = prompt("Enter name for the cloned agent:", `${sourceName}_copy`);
    if (!newName) return;
    
    setBusy(true);
    setStatus(`Cloning ${sourceName}...`);
    try {
      await api("/admin/agents/create", {
        method: "POST",
        body: JSON.stringify({ agent_name: newName, source_agent: sourceName }),
      });
      await refreshAgents();
      setStatus(`Cloned ${sourceName} to ${newName}`);
    } catch (error) {
      setStatus(`Clone failed: ${error.message}`);
    }
    setBusy(false);
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <header className="brand">
          <div>
            <h1>Long River</h1>
            <p>Character Console</p>
          </div>
          <span className={online ? "status online" : "status offline"}>
            {online ? <CheckCircle2 size={16} /> : <TriangleAlert size={16} />}
            {online ? "online" : "offline"}
          </span>
        </header>

        <label>Central Server</label>
        <div className="inline-row">
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          <button className="icon-button" onClick={refreshAgents}><RefreshCw size={18} /></button>
        </div>

        <div className="agent-list">
          <label>Agents</label>
          {agents.map((agent, index) => {
            const pos = agentPosition(agent, index, agentPositions);
            return (
              <button
                key={agent.agent_name}
                className={agent.agent_name === selectedAgent ? "agent-row active" : "agent-row"}
                onClick={() => setSelectedAgent(agent.agent_name)}
              >
                <span><strong>{agent.agent_name}</strong></span>
                <div className="inline-row">
                  <span className={`agent-state ${agent.status}`}>{agent.status}</span>
                  <button 
                    className="icon-button secondary" 
                    title={agent.status === "online" ? "Stop Agent" : "Start Agent"}
                    onClick={(e) => { e.stopPropagation(); handleToggleService(agent); }}
                  >
                    {agent.status === "online" ? <Square size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
                  </button>
                  <button 
                    className="icon-button secondary" 
                    title="Clone Agent"
                    onClick={(e) => { e.stopPropagation(); handleClone(agent.agent_name); }}
                  >
                    <Copy size={14} />
                  </button>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p>{selectedSummary?.metadata?.service_url || status}</p>
            <h2>{selectedAgent || "Select an Agent"}</h2>
          </div>
          <div className="actions">
            <button 
              className={selectedSummary?.status === "online" ? "danger" : "success"}
              disabled={!selectedAgent || busy}
              onClick={() => handleToggleService(selectedSummary)}
            >
              {selectedSummary?.status === "online" ? <Square size={16} /> : <Play size={16} />}
              {selectedSummary?.status === "online" ? "Stop" : "Start"}
            </button>
            <button 
              className="secondary" 
              disabled={!selectedAgent || busy}
              onClick={() => handleClone(selectedAgent)}
            >
              <Copy size={16} /> Clone
            </button>
            <button className="secondary" onClick={() => alert("Check start_all.sh to start new agents.")}><Plus size={16} /> Start</button>
            <button className="danger" disabled={!selectedAgent}><Trash2 size={16} /> Delete</button>
          </div>
        </header>

        <nav className="tabs">
          <button className={activeTab === "graph" ? "active" : ""} onClick={() => setActiveTab("graph")}><Network size={16} /> Network</button>
          <button className={activeTab === "terminal" ? "active" : ""} onClick={() => setActiveTab("terminal")}><TerminalIcon size={16} /> Terminal</button>
          <button className={activeTab === "gemini" ? "active" : ""} onClick={() => setActiveTab("gemini")}><FileText size={16} /> GEMINI.md</button>
          <button className={activeTab === "card" ? "active" : ""} onClick={() => setActiveTab("card")}><Bot size={16} /> AgentCard</button>
        </nav>

        {activeTab === "graph" && (
          <section className="graph-view">
            <div
              ref={graphCanvasRef}
              className={graphGesture?.mode === "pan" ? "graph-canvas panning" : "graph-canvas"}
              onPointerDown={startCanvasGesture}
              onPointerMove={moveCanvasGesture}
              onPointerUp={finishGesture}
            >
              <div className="graph-world" style={{ transform: `translate(${panOffset.x}px, ${panOffset.y}px)` }}>
                <svg className="graph-lines">
                  {edges.map((edge) => {
                    const lIdx = agents.findIndex((a) => a.agent_name === edge.from);
                    const rIdx = agents.findIndex((a) => a.agent_name === edge.to);
                    const lPos = agentPosition(agents[lIdx], lIdx, agentPositions);
                    const rPos = agentPosition(agents[rIdx], rIdx, agentPositions);
                    return <line key={`${edge.from}-${edge.to}`} x1={lPos.x + 86} y1={lPos.y + 48} x2={rPos.x + 86} y2={rPos.y + 48} />;
                  })}
                </svg>
                {agents.map((agent, index) => {
                  const pos = agentPosition(agent, index, agentPositions);
                  return (
                    <div
                      key={agent.agent_name}
                      className={agent.agent_name === selectedAgent ? "graph-agent active" : "graph-agent"}
                      style={{ left: pos.x, top: pos.y }}
                      onPointerDown={(e) => startDrag(e, agent.agent_name, pos)}
                    >
                      <strong>{agent.agent_name}</strong>
                      <span>{agent.status}</span>
                      <small>{(agent.communication_spaces || []).join(", ")}</small>
                    </div>
                  );
                })}
                {cloning && (
                  <div className="graph-agent cloning" style={{ left: cloning.currentX, top: cloning.currentY }}>
                    <strong>{cloning.sourceName} (clone)</strong>
                  </div>
                )}
              </div>
            </div>
            <aside className="space-panel">
              <h3>Spaces</h3>
              <button onClick={addSpace}><Plus size={16} /> Add Space</button>
              <select value={selectedSpaceId} onChange={(e) => setSelectedSpaceId(e.target.value)}>
                {spaces.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <div className="member-list">
                {agents.map((a) => (
                  <button
                    key={a.agent_name}
                    className={(selectedSpace?.members || []).includes(a.agent_name) ? "chip active" : "chip"}
                    onClick={() => toggleSpaceMember(a.agent_name)}
                  >
                    {a.agent_name}
                  </button>
                ))}
              </div>
              <p className="note">Alt + Drag an agent to clone it. Agents in the same space connect automatically.</p>
            </aside>
          </section>
        )}

        {activeTab === "terminal" && (
          <section className="terminal-view">
            <div ref={terminalRef} className="terminal-container" />
          </section>
        )}

        {activeTab === "gemini" && (
          <section className="gemini-view">
            <textarea
              className="gemini-editor"
              value={geminiContent}
              onChange={(e) => setGeminiContent(e.target.value)}
              placeholder="Edit GEMINI.md here..."
            />
            <button onClick={saveGemini} disabled={busy}><Save size={16} /> Save GEMINI.md</button>
          </section>
        )}

        {activeTab === "card" && (
          <section className="gemini-view">
            <textarea
              className="gemini-editor"
              value={cardContent}
              onChange={(e) => setCardContent(e.target.value)}
              placeholder="Edit AgentCard.json here..."
            />
            <button onClick={saveCard} disabled={busy}><Save size={16} /> Save AgentCard.json</button>
          </section>
        )}

        <footer className="footer">
          <span>{busy ? "Working..." : status}</span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
