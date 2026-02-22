from huggingface_hub import snapshot_download
import os

repo_id = "sarvamai/mmlu-indic"
local_dir = "data/mmlu-indic"

print(f"Downloading {repo_id} to {local_dir}...")

snapshot_download(
    repo_id=repo_id, 
    repo_type="dataset", 
    local_dir=local_dir
)

print("Download complete.")
