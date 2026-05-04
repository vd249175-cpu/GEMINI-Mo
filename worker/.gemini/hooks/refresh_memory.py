import sys
import json
import os
import re

def log(msg):
    sys.stderr.write(f"[refresh-memory] {msg}\n")

def find_project_root():
    if 'GEMINI_PROJECT_DIR' in os.environ:
        return os.environ['GEMINI_PROJECT_DIR']
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, 'GEMINI.md')) or \
           os.path.exists(os.path.join(current_dir, '.gemini')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    return os.getcwd()

def normalize_path(path):
    return os.path.normpath(os.path.abspath(path)).lower()

def update_text(text, target_files, files_already_seen_in_system):
    if not isinstance(text, str) or "--- Context from: " not in text:
        return text, False
    
    new_content = text
    start_marker_prefix = "--- Context from: "
    start_pos = 0
    updated = False
    
    while True:
        idx = new_content.find(start_marker_prefix, start_pos)
        if idx == -1:
            break
        
        line_end = new_content.find("\n", idx)
        if line_end == -1:
            line_end = len(new_content)
        
        line = new_content[idx:line_end]
        path_match = re.search(r"--- Context from: (.*?) ---", line)
        if not path_match:
            start_pos = line_end
            continue
        
        found_path = path_match.group(1).strip()
        norm_found_path = normalize_path(found_path)
        
        end_marker = f"--- End of Context from: {found_path} ---"
        end_idx = new_content.find(end_marker, line_end)
        
        if end_idx != -1:
            if norm_found_path in target_files:
                fresh_content = target_files[norm_found_path]
                
                is_redundant = norm_found_path in files_already_seen_in_system
                
                if is_redundant and found_path.lower().endswith("gemini.md"):
                    effective_content = f"\n(Redundant: content already provided in System Instruction)\n"
                else:
                    effective_content = f"\n{fresh_content}\n"
                
                new_block = f"--- Context from: {found_path} ---{effective_content}{end_marker}"
                
                old_block = new_content[idx : end_idx + len(end_marker)]
                if old_block != new_block:
                    before = new_content[:idx]
                    after = new_content[end_idx + len(end_marker):]
                    new_content = before + new_block + after
                    updated = True
                    if is_redundant:
                        log(f"Deduplicated context for {found_path}")
                    else:
                        log(f"Refreshed context for {found_path}")
                
                start_pos = idx + len(new_block)
            else:
                start_pos = end_idx + len(end_marker)
        else:
            start_pos = line_end
            
    return new_content, updated

def update_message_object(msg, target_files, files_already_seen_in_system):
    updated = False
    new_msg = msg.copy()
    
    if "content" in new_msg and isinstance(new_msg["content"], str):
        new_text, text_updated = update_text(new_msg["content"], target_files, files_already_seen_in_system)
        if text_updated:
            new_msg["content"] = new_text
            updated = True
    
    if "parts" in new_msg and isinstance(new_msg["parts"], list):
        new_parts = []
        parts_updated = False
        for part in new_msg["parts"]:
            new_part = part.copy()
            if isinstance(new_part, dict) and "text" in new_part:
                new_text, text_updated = update_text(new_part["text"], target_files, files_already_seen_in_system)
                if text_updated:
                    new_part["text"] = new_text
                    parts_updated = True
            new_parts.append(new_part)
        if parts_updated:
            new_msg["parts"] = new_parts
            updated = True
            
    return new_msg, updated

def get_files_in_system_instructions(messages, target_files):
    seen = set()
    for msg in messages:
        if msg.get("role") == "system":
            content = ""
            if isinstance(msg.get("content"), str):
                content = msg["content"]
            elif isinstance(msg.get("parts"), list):
                for p in msg["parts"]:
                    if isinstance(p, dict) and "text" in p:
                        content += p["text"]
            
            matches = re.findall(r"--- Context from: (.*?) ---", content)
            for m in matches:
                seen.add(normalize_path(m.strip()))
    return seen

def run_hook():
    try:
        if sys.stdin.isatty():
            return
            
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)
        
        llm_request = input_data.get("llm_request")
        if not llm_request:
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        messages = llm_request.get("messages", [])
        system_instruction = llm_request.get("systemInstruction")
        
        project_dir = find_project_root()
        target_files = {} 
        
        project_gemini = os.path.join(project_dir, 'GEMINI.md')
        if os.path.exists(project_gemini):
            with open(project_gemini, 'r') as f:
                target_files[normalize_path(project_gemini)] = f.read()
        
        try:
            settings_path = os.path.join(project_dir, '.gemini/settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    include_dirs = settings.get('context', {}).get('includeDirectories', [])
                    for d in include_dirs:
                        abs_d = os.path.abspath(os.path.join(project_dir, d))
                        gemini_md = os.path.join(abs_d, 'GEMINI.md')
                        if os.path.exists(gemini_md):
                            with open(gemini_md, 'r') as f:
                                target_files[normalize_path(gemini_md)] = f.read()
        except Exception as e:
            log(f"Error loading settings: {e}")
        
        if not target_files:
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        request_overrides = {}
        any_updated = False

        files_in_system = get_files_in_system_instructions(messages, target_files)
        if system_instruction:
            content = ""
            if isinstance(system_instruction.get("content"), str):
                content = system_instruction["content"]
            elif isinstance(system_instruction.get("parts"), list):
                for p in system_instruction["parts"]:
                    if isinstance(p, dict) and "text" in p:
                        content += p["text"]
            matches = re.findall(r"--- Context from: (.*?) ---", content)
            for m in matches:
                files_in_system.add(normalize_path(m.strip()))

        if system_instruction:
            new_si, si_updated = update_message_object(system_instruction, target_files, set())
            if si_updated:
                request_overrides["systemInstruction"] = new_si
                any_updated = True

        new_messages = []
        messages_modified = False
        for msg in messages:
            is_si = (msg.get("role") == "system")
            new_msg, msg_updated = update_message_object(
                msg, 
                target_files, 
                set() if is_si else files_in_system
            )
            
            if msg_updated:
                messages_modified = True
                any_updated = True
            new_messages.append(new_msg)

        if messages_modified:
            request_overrides["messages"] = new_messages

        if not any_updated:
            print(json.dumps({"decision": "allow", "continue": True}))
            return

        print(json.dumps({
            "decision": "allow",
            "continue": True,
            "hookSpecificOutput": {
                "llm_request": request_overrides
            }
        }))
    except Exception as e:
        log(f"Critical error: {str(e)}")
        print(json.dumps({"decision": "allow", "continue": True}))

if __name__ == "__main__":
    run_hook()
