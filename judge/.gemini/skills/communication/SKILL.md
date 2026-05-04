# Communication Skill

This skill allows the agent to send messages to other agents registered with the Central Server.

## Tools

### send_message
Sends a message to a target agent.

**Parameters:**
- `to`: (required) The name of the target agent (e.g., "judge", "worker").
- `content`: (required) The message body to send.

**Usage:**
```bash
python3 scripts/send_message.py --to "judge" --content "The image has been generated."
```
