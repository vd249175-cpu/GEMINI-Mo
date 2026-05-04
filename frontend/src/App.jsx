import React, { useEffect, useMemo, useRef, useState } from "react";
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
  Globe,
  User,
  Settings,
  ChevronRight,
  Monitor,
  Moon,
  Sun
} from "lucide-react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import "./App.css";

const i18n = {
  en: {
    title: "Character Console",
    online: "online",
    offline: "offline",
    centralServer: "Central Server",
    agents: "Agents",
    selectAgent: "Select an Agent",
    start: "Start",
    stop: "Stop",
    clone: "Clone",
    delete: "Delete",
    network: "Network",
    terminal: "Terminal",
    spaces: "Spaces",
    addSpace: "Add Space",
    working: "Working...",
    ready: "Ready",
    connected: "Connected",
    saveGemini: "Save GEMINI.md",
    saveCard: "Save AgentCard",
    editGemini: "Edit GEMINI.md here...",
    editCard: "Edit AgentCard.json here...",
    langSwitch: "中/EN",
    status: "Status",
    newSpacePrompt: "New space name:",
    clonePrompt: "Enter name for the cloned agent:",
    deleteConfirm: "Are you sure you want to delete {agent}?",
  },
  zh: {
    title: "角色控制台",
    online: "在线",
    offline: "离线",
    centralServer: "中央服务器",
    agents: "智能体列表",
    selectAgent: "请选择一个智能体",
    start: "启动",
    stop: "停止",
    clone: "克隆",
    delete: "删除",
    network: "网络拓扑",
    terminal: "终端",
    spaces: "通讯空间",
    addSpace: "添加空间",
    working: "处理中...",
    ready: "就绪",
    connected: "已连接",
    saveGemini: "保存 GEMINI.md",
    saveCard: "保存 AgentCard",
    editGemini: "在此处编辑 GEMINI.md...",
    editCard: "在此处编辑 AgentCard.json...",
    langSwitch: "中/EN",
    status: "状态",
    newSpacePrompt: "新空间名称：",
    clonePrompt: "请输入克隆出的 Agent 名称：",
    deleteConfirm: "确定要删除 {agent} 吗？",
  }
};

function shortId(prefix = "") {
  return `${prefix}${Math.random().toString(36).slice(2, 10)}`;
}

function buildEdges(spaces, agentNames) {
  const allowed = new Set(agentNames);
  const edgeMap = new Map();
  for (const space of spaces) {
    const members = (space.members || []).filter((name) => allowed.has(name));
    for (let i = 0; i < members.length; i += 1) {
      for (let j = i + 1; j < members.length; j += 1) {
        const key = [members[i], members[j]].sort().join("::");
        const existing = edgeMap.get(key) || { from: members[i], to: members[j], spaces: [] };
        existing.spaces.push(space.id);
        edgeMap.set(key, existing);
      }
    }
  }
  return [...edgeMap.values()];
}

function App() {
  const defaultUrl = (typeof import.meta.env !== 'undefined' && import.meta.env.VITE_CENTRAL_URL) ? import.meta.env.VITE_CENTRAL_URL : "http://127.0.0.1:8000";
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("centralUrl") || defaultUrl);
  const [agents, setAgents] = useState([]);
  const [communication, setCommunication] = useState({ spaces: [] });
  const [selectedAgent, setSelectedAgent] = useState("");
  const [selectedSpaceId, setSelectedSpaceId] = useState("");
  const [activeTab, setActiveTab] = useState("graph");
  const [lang, setLang] = useState(localStorage.getItem("lang") || "en");
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  
  const t = (key, params) => {
    let str = i18n[lang][key] || key;
    if (params) {
      Object.keys(params).forEach((k) => (str = str.replace(`{${k}}`, params[k])));
    }
    return str;
  };

  const [status, setStatus] = useState(t("ready"));
  const [online, setOnline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [geminiContent, setGeminiContent] = useState("");
  const [cardContent, setCardContent] = useState("{}");

  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [agentPositions, setAgentPositions] = useState(() => {
    try {
      const saved = localStorage.getItem("agentPositions");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  const [dragging, setDragging] = useState(null);
  const [graphGesture, setGraphGesture] = useState(null);

  useEffect(() => {
    localStorage.setItem("agentPositions", JSON.stringify(agentPositions));
  }, [agentPositions]);

  const terminalContainerRef = useRef(null);
  const terminalsMap = useRef({});
  const graphCanvasRef = useRef(null);

  const selectedSummary = agents.find((agent) => agent.agent_name === selectedAgent);
  const spaces = communication.spaces || [];
  const selectedSpace = spaces.find((s) => s.id === selectedSpaceId) || spaces[0] || null;
  const edges = useMemo(() => buildEdges(spaces, agents.map(a => a.agent_name)), [spaces, agents]);

  const api = async (path, options = {}) => {
    const root = baseUrl.replace(/\/$/, "");
    const headers = { ...(options.headers || {}) };
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(`${root}${path}`, {
      ...options,
      headers,
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  };

  const agentApi = async (path, options = {}) => {
    if (!selectedSummary?.metadata?.service_url) throw new Error("Agent service URL not found");
    const headers = { ...(options.headers || {}) };
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(`${selectedSummary.metadata.service_url}${path}`, {
      ...options,
      headers,
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
    } catch (error) {
      setOnline(false);
    }
  };

  useEffect(() => {
    refreshAgents();
    const timer = setInterval(refreshAgents, 3000);
    return () => clearInterval(timer);
  }, [baseUrl]);

  // Load Content
  useEffect(() => {
    if (selectedAgent && selectedSummary?.status === "online") {
      if (activeTab === "gemini") {
        agentApi("/gemini").then((res) => setGeminiContent(res.content || "")).catch(() => {});
      } else if (activeTab === "card") {
        agentApi("/card").then((res) => setCardContent(JSON.stringify(res.card || {}, null, 2))).catch(() => {});
      }
    }
  }, [activeTab, selectedAgent, selectedSummary]);

  const serviceUrl = selectedSummary?.metadata?.service_url;

  // Terminal Logic
  useEffect(() => {
    if (activeTab !== "terminal" || !selectedAgent || !serviceUrl) return;

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
      
      const wsUrl = serviceUrl.replace(/^http/, "ws") + "/terminal";
      const socket = new WebSocket(wsUrl);
      socket.binaryType = "arraybuffer";
      socket.onmessage = (event) => {
        term.write(new Uint8Array(event.data));
        term.scrollToBottom();
      };
      term.onData((data) => {
        if (data === "\x1b[?1;2c" || data === "\x1b[?6c") return;
        if (socket.readyState === WebSocket.OPEN) socket.send(data);
      });

      entry = { term, fitAddon, socket };
      terminalsMap.current[agentName] = entry;
    }

    const { term, fitAddon, socket } = entry;

    const handleResize = () => {
      if (!terminalContainerRef.current) return;
      try {
        fitAddon.fit();
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
        }
      } catch (e) {}
    };

    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });

    if (terminalContainerRef.current) {
      if (!term.element || !terminalContainerRef.current.contains(term.element)) {
        terminalContainerRef.current.innerHTML = "";
        if (term.element) {
          terminalContainerRef.current.appendChild(term.element);
        } else {
          term.open(terminalContainerRef.current);
        }
      }
      resizeObserver.observe(terminalContainerRef.current);
    }
    
    setTimeout(handleResize, 50);
    term.focus();

    return () => {
      resizeObserver.disconnect();
    };
  }, [activeTab, selectedAgent, serviceUrl]);

  // Graph Gesture
  const getGraphPos = (agent, index) => {
    return agentPositions[agent.agent_name] || { x: 100 + (index % 3) * 200, y: 100 + Math.floor(index / 3) * 140 };
  };

  const handlePointerDown = (e) => {
    if (e.target.closest(".graph-agent-node") || e.target.closest(".floating-panel")) return;
    setGraphGesture({ startX: e.clientX, startY: e.clientY, originX: panOffset.x, originY: panOffset.y });
  };

  const handlePointerMove = (e) => {
    if (dragging) {
      const dx = e.clientX - dragging.startX;
      const dy = e.clientY - dragging.startY;
      setAgentPositions(prev => ({
        ...prev,
        [dragging.name]: { x: dragging.originX + dx, y: dragging.originY + dy }
      }));
      return;
    }
    if (graphGesture) {
      setPanOffset({
        x: graphGesture.originX + e.clientX - graphGesture.startX,
        y: graphGesture.originY + e.clientY - graphGesture.startY
      });
    }
  };

  const handlePointerUp = () => {
    setGraphGesture(null);
    setDragging(null);
  };

  // Actions
  const handleToggleService = async (agent) => {
    if (!agent) return;
    setBusy(true);
    const action = agent.status === "online" ? "stop" : "start";
    setStatus(`${action === "start" ? "Starting" : "Stopping"} ${agent.agent_name}...`);
    try {
      await api(`/admin/agents/${agent.agent_name}/${action}`, { method: "POST" });
      await refreshAgents();
      setStatus(`${agent.agent_name} ${action}ed`);
    } catch (error) {
      console.error(error);
      setStatus(`Action failed: ${error.message}`);
      alert(`Action failed: ${error.message}`);
    }
    setBusy(false);
  };

  const handleClone = async (sourceName) => {
    const newName = prompt(t("clonePrompt"), `${sourceName}_copy`);
    if (!newName) return;
    setBusy(true);
    try {
      await api("/admin/agents/create", { method: "POST", body: JSON.stringify({ agent_name: newName, source_agent: sourceName }) });
      refreshAgents();
    } catch (error) {
      alert(error.message);
    }
    setBusy(false);
  };

  const handleDelete = async (agentName) => {
    if (!confirm(t("deleteConfirm", { agent: agentName }))) return;
    setBusy(true);
    try {
      await api(`/admin/agents/${agentName}`, { method: "DELETE" });
      if (selectedAgent === agentName) setSelectedAgent("");
      setAgentPositions(prev => {
        const next = { ...prev };
        delete next[agentName];
        return next;
      });
      refreshAgents();
    } catch (error) {
      alert(error.message);
    }
    setBusy(false);
  };

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
    const name = prompt(t("newSpacePrompt"));
    if (!name) return;
    const newId = shortId("space-");
    const nextSpaces = [...spaces, { id: newId, name, color: "#2563eb", members: [] }];
    api("/admin/communication", { method: "PUT", body: JSON.stringify({ spaces: nextSpaces }) }).then(() => {
      setSelectedSpaceId(newId);
      refreshAgents();
    });
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <h1>GEMINI-MO</h1>
            <p className="sidebar-port-text">{baseUrl}</p>
          </div>
        </div>

        <div className="sidebar-section" style={{ flex: 1, overflow: 'auto' }}>
          <div className="sidebar-label">{t("agents")}</div>
          {agents.map((agent) => (
            <button 
              key={agent.agent_name}
              className={`nav-item ${selectedAgent === agent.agent_name ? 'active' : ''}`}
              onClick={() => setSelectedAgent(agent.agent_name)}
            >
              <div className="nav-item-icon">
                <div className={`nav-item-status ${agent.status === 'online' ? 'status-online' : 'status-offline'}`} />
              </div>
              <div className="nav-item-content">{agent.agent_name}</div>
              <ChevronRight size={14} style={{ opacity: 0.3 }} />
            </button>
          ))}
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-info">
            <div className="topbar-title">{selectedAgent || t("selectAgent")}</div>
            <div className="topbar-subtitle">{selectedSummary?.metadata?.service_url || "No service URL"}</div>
          </div>
          <div className="topbar-actions">
            <button className="btn btn-secondary" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} title="Toggle Theme">
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
            <button className="btn btn-secondary" onClick={() => setLang(lang === 'en' ? 'zh' : 'en')} style={{ fontWeight: 600 }}>
              {t("langSwitch")}
            </button>
            <button 
              className={`btn ${selectedSummary?.status === 'online' ? 'btn-danger' : 'btn-primary'}`}
              disabled={!selectedAgent || busy}
              onClick={() => handleToggleService(selectedSummary)}
            >
              {selectedSummary?.status === 'online' ? <Square size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
              {selectedSummary?.status === 'online' ? t("stop") : t("start")}
            </button>
            <button className="btn btn-secondary" disabled={!selectedAgent} onClick={() => handleClone(selectedAgent)}>
              <Copy size={14} /> {t("clone")}
            </button>
            <button className="btn btn-danger" disabled={!selectedAgent} onClick={() => handleDelete(selectedAgent)}>
              <Trash2 size={14} />
            </button>
          </div>
        </header>

        <nav className="tabs-container">
          <button className={`tab ${activeTab === 'graph' ? 'active' : ''}`} onClick={() => setActiveTab('graph')}>
            <Network size={16} /> {t("network")}
          </button>
          <button className={`tab ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}>
            <TerminalIcon size={16} /> {t("terminal")}
          </button>
          <button className={`tab ${activeTab === 'gemini' ? 'active' : ''}`} onClick={() => setActiveTab('gemini')}>
            <FileText size={16} /> GEMINI.md
          </button>
          <button className={`tab ${activeTab === 'card' ? 'active' : ''}`} onClick={() => setActiveTab('card')}>
            <Bot size={16} /> AgentCard
          </button>
        </nav>

        <div className="view-container">
          {activeTab === 'graph' && (
            <div 
              className="graph-view fade-in"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              ref={graphCanvasRef}
            >
              <div style={{ position: 'absolute', inset: 0, transform: `translate(${panOffset.x}px, ${panOffset.y}px)` }}>
                <svg style={{ position: 'absolute', inset: 0, width: 2000, height: 2000, pointerEvents: 'none' }}>
                  {[...edges].sort((a, b) => {
                    const aSel = a.spaces.includes(selectedSpaceId);
                    const bSel = b.spaces.includes(selectedSpaceId);
                    return aSel === bSel ? 0 : aSel ? 1 : -1;
                  }).map(edge => {
                    const lIdx = agents.findIndex(a => a.agent_name === edge.from);
                    const rIdx = agents.findIndex(a => a.agent_name === edge.to);
                    if (lIdx === -1 || rIdx === -1) return null;
                    const p1 = getGraphPos(agents[lIdx], lIdx);
                    const p2 = getGraphPos(agents[rIdx], rIdx);
                    const isSelected = edge.spaces.includes(selectedSpaceId);
                    const color = isSelected ? (selectedSpace?.color || "#2563eb") : "#e2e8f0";
                    const width = isSelected ? 2 : 1;
                    return <line key={`${edge.from}-${edge.to}`} x1={p1.x + 80} y1={p1.y + 30} x2={p2.x + 80} y2={p2.y + 30} stroke={color} strokeWidth={width} />;
                  })}
                </svg>
                {agents.map((agent, index) => {
                  const pos = getGraphPos(agent, index);
                  return (
                    <div 
                      key={agent.agent_name}
                      className={`graph-agent-node ${selectedAgent === agent.agent_name ? 'active' : ''}`}
                      style={{ left: pos.x, top: pos.y }}
                      onPointerDown={(e) => {
                        e.stopPropagation();
                        setSelectedAgent(agent.agent_name);
                        setDragging({ name: agent.agent_name, startX: e.clientX, startY: e.clientY, originX: pos.x, originY: pos.y });
                      }}
                    >
                      <h3>{agent.agent_name}</h3>
                      <p>{agent.status === 'online' ? t("online") : t("offline")}</p>
                    </div>
                  );
                })}
              </div>

              {/* Floating Spaces Panel */}
              <div className="floating-panel" onPointerDown={(e) => e.stopPropagation()}>
                <div className="floating-panel-title">{t("spaces")}</div>
                <select 
                  className="input" 
                  value={selectedSpaceId} 
                  onChange={(e) => setSelectedSpaceId(e.target.value)}
                >
                  {spaces.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {agents.map(a => (
                    <button 
                      key={a.agent_name}
                      className={`btn btn-secondary ${selectedSpace?.members?.includes(a.agent_name) ? 'active' : ''}`}
                      style={{ height: 26, fontSize: 12, padding: '0 10px', borderColor: selectedSpace?.members?.includes(a.agent_name) ? 'var(--accent-blue)' : 'var(--border-color)' }}
                      onClick={() => toggleSpaceMember(a.agent_name)}
                    >
                      {a.agent_name}
                    </button>
                  ))}
                </div>
                <button className="btn btn-secondary" style={{ width: '100%', height: 32 }} onClick={addSpace}>
                  <Plus size={16} /> {t("addSpace")}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'terminal' && (
            <div className="terminal-view fade-in">
              <div ref={terminalContainerRef} className="terminal-container" />
            </div>
          )}

          {(activeTab === 'gemini' || activeTab === 'card') && (
            <div className="editor-view fade-in">
              <textarea 
                className="editor-textarea" 
                value={activeTab === 'gemini' ? geminiContent : cardContent}
                onChange={(e) => activeTab === 'gemini' ? setGeminiContent(e.target.value) : setCardContent(e.target.value)}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn btn-primary" onClick={activeTab === 'gemini' ? saveGemini : saveCard} disabled={busy}>
                  <Save size={16} /> Save
                </button>
              </div>
            </div>
          )}
        </div>

        <footer className="footer">
          <Activity size={14} style={{ marginRight: 6 }} />
          {online ? t("connected") : t("offline")} | {busy ? t("working") : t("ready")}
        </footer>
      </main>
    </div>
  );
}

export default App;
