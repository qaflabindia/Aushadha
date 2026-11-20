"""Upload the demo PDFs for the demo patient and build their knowledge graph.

Run inside the backend container after seed_demo.py (deploy/remote-setup.sh does this):
    docker exec -i -w /code -e ADMIN_EMAIL backend python - < deploy/seed_demo_docs.py

Goes through the same API the web app uses (upload, extract, post-processing), signed in
as the admin. PDFs come from /demo_docs. Files that are already Completed are skipped,
so the script can be re-run after a failure.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

from src.shared.google_auth import create_local_token

API = os.environ.get("API", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
CASE_ID = os.environ.get("DEMO_CASE_ID", "PAT-DEMO-HTN")
MODEL = os.environ.get("DEMO_MODEL", "gemini_3.1_pro")
DOCS = Path(os.environ.get("DEMO_DOCS", "/demo_docs"))
POST_TASKS = [
    "materialize_text_chunk_similarities",
    "enable_hybrid_search_and_fulltext_search_in_bloom",
    "materialize_entity_similarities",
    "enable_communities",
]


def main() -> int:
    if not ADMIN_EMAIL:
        print("ADMIN_EMAIL is required", file=sys.stderr)
        return 1
    files = sorted(DOCS.glob("*.pdf"), key=lambda p: int(p.name.split("_")[1]) if p.name.split("_")[1].isdigit() else 0)
    if not files:
        print(f"No PDFs in {DOCS}", file=sys.stderr)
        return 1

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {create_local_token(ADMIN_EMAIL, 'Demo seeder')}"
    base = {"email": ADMIN_EMAIL, "user_role": "Admin", "patient_id": CASE_ID}

    listed = s.post(f"{API}/sources_list", data=base, timeout=60).json().get("data") or []
    done = {f.get("fileName") for f in listed if f.get("status") == "Completed"}

    failed = []
    for i, path in enumerate(files, 1):
        name = path.name
        if name in done:
            print(f"[{i}/{len(files)}] {name}: already Completed, skipped", flush=True)
            continue
        with path.open("rb") as fh:
            up = s.post(
                f"{API}/upload",
                data={**base, "chunkNumber": 1, "totalChunks": 1, "originalname": name, "model": MODEL},
                files={"file": (name, fh, "application/pdf")},
                timeout=120,
            ).json()
        if up.get("status") != "Success":
            print(f"[{i}/{len(files)}] {name}: upload failed: {up.get('message')}", flush=True)
            failed.append(name)
            continue
        t = time.time()
        ex = s.post(
            f"{API}/extract",
            data={
                **base,
                "model": MODEL,
                "source_type": "local file",
                "file_name": name,
                "token_chunk_size": 200,
                "chunk_overlap": 20,
                "chunks_to_combine": 1,
                "retry_condition": "",
            },
            timeout=1800,
        ).json()
        ok = ex.get("status") == "Success"
        detail = ex.get("data") or {}
        print(
            f"[{i}/{len(files)}] {name}: {'ok' if ok else 'FAILED'} in {time.time() - t:.0f}s"
            + (f", {detail.get('nodeCount')} nodes, {detail.get('relationshipCount')} relationships" if ok else f": {ex.get('message') or ex.get('error')}"),
            flush=True,
        )
        if not ok:
            failed.append(name)

    pp = s.post(f"{API}/post_processing", data={**base, "tasks": json.dumps(POST_TASKS)}, timeout=1800).json()
    print(f"post-processing: {pp.get('status')}", flush=True)

    if failed:
        print(f"{len(failed)} file(s) failed: {', '.join(failed)}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
