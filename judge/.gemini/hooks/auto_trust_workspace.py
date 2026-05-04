import sys
import json
import os

def log(msg):
    sys.stderr.write(f"[auto-trust-workspace] {msg}\n")

def find_project_root():
    if 'GEMINI_PROJECT_DIR' in os.environ:
        return os.environ['GEMINI_PROJECT_DIR']
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):
        if os.path.exists(os.path.join(current_dir, '.gemini')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    return os.getcwd()

def update_trusted_folders(parent_dir, workspace_dir):
    trusted_file = os.path.expanduser('~/.gemini/trustedFolders.json')
    if not os.path.exists(trusted_file):
        trusted_data = {}
    else:
        try:
            with open(trusted_file, 'r') as f:
                trusted_data = json.load(f)
        except Exception as e:
            log(f"Error reading trusted folders: {e}")
            trusted_data = {}
    
    changed = False
    # Normalizing paths to absolute
    parent_dir = os.path.abspath(parent_dir)
    workspace_dir = os.path.abspath(workspace_dir)
    
    if parent_dir not in trusted_data:
        trusted_data[parent_dir] = "TRUST_FOLDER"
        changed = True
        log(f"Adding {parent_dir} to trusted folders")
    if workspace_dir not in trusted_data:
        trusted_data[workspace_dir] = "TRUST_FOLDER"
        changed = True
        log(f"Adding {workspace_dir} to trusted folders")
    
    if changed:
        try:
            with open(trusted_file, 'w') as f:
                json.dump(trusted_data, f, indent=2)
            return True
        except Exception as e:
            log(f"Error writing trusted folders: {e}")
            return False
    return False

def update_project_settings(project_dir, workspace_dir):
    settings_file = os.path.join(project_dir, '.gemini/settings.json')
    if not os.path.exists(settings_file):
        log(f"Settings file not found: {settings_file}")
        return False
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        log(f"Error reading settings: {e}")
        return False
    
    changed = False
    if 'context' not in settings:
        settings['context'] = {}
        changed = True
    if 'includeDirectories' not in settings['context']:
        settings['context']['includeDirectories'] = []
        changed = True
    
    # Use path relative to project_dir for includeDirectories
    rel_workspace = os.path.relpath(workspace_dir, project_dir)
    if rel_workspace not in settings['context']['includeDirectories']:
        settings['context']['includeDirectories'].append(rel_workspace)
        changed = True
        log(f"Adding {rel_workspace} to includeDirectories")
    
    if changed:
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            log(f"Error writing settings: {e}")
            return False
    return False

def run_hook():
    try:
        # Read from stdin to consume the event data
        if not sys.stdin.isatty():
            try:
                input_data = json.load(sys.stdin)
                source = input_data.get("source", "unknown")
                log(f"Running for SessionStart (source: {source})")
            except:
                pass

        project_dir = find_project_root()
        parent_dir = os.path.dirname(project_dir)
        workspace_dir = os.path.join(parent_dir, 'workspace')
        
        # Ensure workspace exists
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir, exist_ok=True)
            log(f"Created workspace directory: {workspace_dir}")
        
        updated_trust = update_trusted_folders(parent_dir, workspace_dir)
        updated_settings = update_project_settings(project_dir, workspace_dir)
        
        msg = ""
        if updated_trust or updated_settings:
            msg = "Updated trusted folders and workspace settings."
        
        output = {
            "decision": "allow",
            "continue": True,
            "hookSpecificOutput": {}
        }
        if msg:
            output["systemMessage"] = msg
            
        print(json.dumps(output))
    except Exception as e:
        log(f"Error in hook execution: {e}")
        print(json.dumps({
            "decision": "allow",
            "continue": True,
            "hookSpecificOutput": {}
        }))

if __name__ == "__main__":
    run_hook()
