from huggingface_hub import snapshot_download
import os

def download_resource(repo_id, local_dir, repo_type="model"):
    print(f"Downloading {repo_id} ({repo_type}) to {local_dir}...")
    try:
        snapshot_download(
            repo_id=repo_id, 
            repo_type=repo_type, 
            local_dir=local_dir,
            max_workers=4
        )
        print(f"Successfully downloaded {repo_id}")
    except Exception as e:
        print(f"Error downloading {repo_id}: {e}")

# MMLU-Indic Dataset
download_resource("sarvamai/mmlu-indic", "data/mmlu-indic", repo_type="dataset")

# Sarvam-2B Model (optimized for local indic tasks)
download_resource("sarvamai/sarvam-1", "data/models/sarvam-2b", repo_type="model")

print("All downloads complete.")
