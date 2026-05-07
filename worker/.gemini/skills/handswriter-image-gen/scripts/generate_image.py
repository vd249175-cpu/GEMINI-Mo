import argparse
import base64
import copy
import json
import os
import random
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

def log(msg):
    sys.stderr.write(f"[image-gen] {msg}\n")

class ComfyUIService:
    def __init__(self, base_url, workflow_path, output_dir):
        self.base_url = base_url.rstrip("/")
        self.workflow_path = Path(workflow_path)
        self.output_base_dir = Path(output_dir)
        self.prompt_node_id = "88:94"
        self.seed_node_id = "88:70"
        self.save_image_node_id = "73"
        self.latent_node_id = "88:71"
        self.width_preview_node_id = "88:99"
        self.height_preview_node_id = "88:100"
        self.timeout_seconds = 300
        self.poll_seconds = 1.0

    def load_workflow(self):
        with open(self.workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def post_json(self, path, payload):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_json(self, path):
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_next_index_dir(self):
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        existing_indices = []
        for d in self.output_base_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                existing_indices.append(int(d.name))
        
        next_index = max(existing_indices) + 1 if existing_indices else 0
        return self.output_base_dir / str(next_index)

    def generate(self, prompt, width, height, workflow_name, negative_prompt=None, seed=None):
        if seed is None:
            seed = random.randint(0, 2**63 - 1)
        
        workflow = self.load_workflow()
        
        # Determine node IDs based on workflow
        # m1 (standard) uses 88:94 for prompt
        # m2 (enhanced) uses 88:78 for prompt input
        prompt_node = "88:78" if workflow_name == "m2" else "88:94"
        
        # Inject prompt
        if prompt_node in workflow:
            workflow[prompt_node]["inputs"]["value"] = prompt
        else:
            log(f"Warning: Prompt node {prompt_node} not found in {workflow_name} workflow")
        
        # Inject negative prompt (if applicable)
        if negative_prompt:
            if workflow_name == "m2":
                if "88:72" in workflow:
                    workflow["88:72"]["inputs"]["text"] = negative_prompt
                else:
                    log("Warning: Negative prompt node 88:72 not found in m2 workflow")
            else:
                log(f"Warning: Workflow {workflow_name} does not support manual negative prompt input")
        
        # Inject seed
        if self.seed_node_id in workflow:
            workflow[self.seed_node_id]["inputs"]["seed"] = seed
            
        # Inject dimensions
        if self.latent_node_id in workflow:
            workflow[self.latent_node_id]["inputs"]["width"] = width
            workflow[self.latent_node_id]["inputs"]["height"] = height
        
        # m1 dimension preview nodes
        if self.width_preview_node_id in workflow:
            workflow[self.width_preview_node_id]["inputs"]["source"] = width
        if self.height_preview_node_id in workflow:
            workflow[self.height_preview_node_id]["inputs"]["source"] = height
            
        # m2 specific dimension nodes (PreviewAny)
        if workflow_name == "m2":
            if "88:92" in workflow: workflow["88:92"]["inputs"]["source"] = width
            if "88:93" in workflow: workflow["88:93"]["inputs"]["source"] = height

        # Queue prompt
        client_id = str(random.getrandbits(128))
        log(f"Queueing prompt with seed {seed}...")
        response = self.post_json("/prompt", {"prompt": workflow, "client_id": client_id})
        prompt_id = response["prompt_id"]
        
        # Wait for completion
        log(f"Waiting for prompt {prompt_id}...")
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            history = self.get_json(f"/history/{prompt_id}")
            if prompt_id in history:
                result = history[prompt_id]
                break
            time.sleep(self.poll_seconds)
        else:
            raise TimeoutError("ComfyUI timeout")

        # Download image
        outputs = result.get("outputs", {})
        save_output = outputs.get(self.save_image_node_id, {})
        images = save_output.get("images", [])
        if not images:
            raise ValueError("No images found in output")
        
        image_info = images[0]
        query = urllib.parse.urlencode(image_info)
        log(f"Downloading image {image_info['filename']}...")
        with urllib.request.urlopen(f"{self.base_url}/view?{query}") as response:
            image_bytes = response.read()

        # Prepare directories
        target_dir = self._get_next_index_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        newest_dir = self.output_base_dir / "newest"
        if newest_dir.exists():
            shutil.rmtree(newest_dir)
        newest_dir.mkdir(parents=True, exist_ok=True)

        # Save image and prompt to target directory
        image_filename = "image.png"
        image_path = target_dir / image_filename
        image_path.write_bytes(image_bytes)
        prompt_path = target_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        
        # Copy to newest directory
        shutil.copy2(image_path, newest_dir / image_filename)
        shutil.copy2(prompt_path, newest_dir / "prompt.txt")
        
        return {
            "image_path": str(image_path),
            "prompt_path": str(prompt_path),
            "newest_dir": str(newest_dir)
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative_prompt", help="Negative prompt (only supported in m2)")
    parser.add_argument("--orientation", choices=["横向", "纵向"], default="横向")
    parser.add_argument("--workflow", choices=["m1", "m2"], default="m1")
    parser.add_argument("--output_dir", default="images")
    parser.add_argument("--base_url", default="http://192.168.5.155:8000")
    
    args = parser.parse_args()
    
    # Resolve shorthand workflow names to actual file paths
    script_dir = Path(__file__).parent
    workflow_path = script_dir.parent / "assets" / "workflows" / f"{args.workflow}.json"
    
    if args.orientation == "横向":
        width, height = 1280, 720
    else:
        width, height = 720, 1280
        
    service = ComfyUIService(args.base_url, workflow_path, args.output_dir)
    try:
        result = service.generate(args.prompt, width, height, args.workflow, negative_prompt=args.negative_prompt)
        print(json.dumps(result, indent=2))
    except Exception as e:
        log(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
