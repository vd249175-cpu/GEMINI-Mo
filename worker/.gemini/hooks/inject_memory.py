"""
inject_memory.py — SessionStart hook

Fires ONCE when a new Gemini CLI session starts (including /clear).
Reads GEMINI.md and injects it as additionalContext so the model
always has the latest instructions at the very beginning of the session,
regardless of how Gemini CLI builds the native systemInstruction.
"""

import sys
import json
import os


def log(msg: str) -> None:
    sys.stderr.write(f"[inject-memory] {msg}\n")
    sys.stderr.flush()


def find_project_root() -> str:
    if "GEMINI_PROJECT_DIR" in os.environ:
        return os.environ["GEMINI_PROJECT_DIR"]
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, ".gemini")):
            return current
        current = os.path.dirname(current)
    return os.getcwd()


def run_hook() -> None:
    try:
        # Consume stdin (SessionStart provides source field)
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
                data = json.loads(raw) if raw.strip() else {}
                source = data.get("source", "unknown")
                log(f"SessionStart source={source}")
            except Exception:
                pass

        project_dir = find_project_root()
        gemini_md = os.path.join(project_dir, "GEMINI.md")

        if not os.path.exists(gemini_md):
            log("GEMINI.md not found, skipping injection")
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        with open(gemini_md, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            log("GEMINI.md is empty, skipping injection")
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        agent_name = os.path.basename(project_dir)
        log(f"Injecting GEMINI.md ({len(content)} chars) for agent '{agent_name}'")

        # SessionStart supports additionalContext via hookSpecificOutput
        print(json.dumps({
            "decision": "allow",
            "continue": True,
            "hookSpecificOutput": {
                "additionalContext": f"[SESSION MEMORY — {agent_name}]\n\n{content}\n[/SESSION MEMORY]"
            }
        }))

    except Exception as e:
        log(f"Critical error: {e}")
        import traceback
        log(traceback.format_exc())
        print(json.dumps({"decision": "allow", "continue": True}))


if __name__ == "__main__":
    run_hook()
