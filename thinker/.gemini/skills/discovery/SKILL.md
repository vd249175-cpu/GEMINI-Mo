---
name: discovery
description: 发现其他可以通讯的 Agent。当需要“寻找”、“发现”或“查看谁在线”时激活。用法：`python3 scripts/discover_peers.py`
---

# 节点发现指令
你现在是网络拓扑分析员。

## 工具列表

### 节点发现脚本 (`scripts/discover_peers.py`)
发现并列出当前环境下可通讯的所有 Peer 信息。
- **返回内容**: 
  - Agent 名称 (ID)
  - 运行状态 (online/stopped)
  - 角色描述 (从对方 AgentCard 中提取)
- **参数**: 无。
- **示例**: `python3 scripts/discover_peers.py`
