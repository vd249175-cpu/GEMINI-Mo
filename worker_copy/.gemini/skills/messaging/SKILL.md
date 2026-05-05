---
name: messaging
description: 发送消息或文件给其他 Agent。当需要“发送”、“通知”或“转交”给其他节点时激活。用法：`python3 scripts/send_message.py --to <name> --content <text> [--files <paths>]`
---

# 消息通讯指令
你现在是系统通讯员。

## 工具列表

### 消息发送脚本 (`scripts/send_message.py`)
用于投递消息和文件。
- **参数**:
  - `--to`: 目标名称 (必填)
  - `--content`: 消息正文 (必填)
  - `--files`: 附件路径 (可选)

- **示例**:
  `python3 scripts/send_message.py --to "judge" --content "任务完成" --files "./data.zip"`
