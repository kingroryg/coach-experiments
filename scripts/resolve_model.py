#!/usr/bin/env python3
"""Resolve MODEL_PATH to a local GGUF file path.

If MODEL_PATH is a local file, return it as-is.
If MODEL_PATH looks like a HuggingFace repo ID, download it and return the first GGUF file.
"""
import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files


def resolve_model(model_path: str) -> str:
    # Check if it's a local file
    if os.path.exists(model_path):
        return model_path

    # Treat as HuggingFace repo ID
    token = os.getenv("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN environment variable required for downloading models", file=sys.stderr)
        sys.exit(1)

    try:
        # List files in the repo
        files = list_repo_files(repo_id=model_path, token=token)
        gguf_files = [f for f in files if f.lower().endswith(".gguf")]

        if not gguf_files:
            print(f"ERROR: No GGUF files found in {model_path}", file=sys.stderr)
            sys.exit(1)

        # Download the first GGUF file
        filename = gguf_files[0]
        local_dir = Path("models") / model_path.replace("/", "__")
        local_path = local_dir / filename

        # If already downloaded, return it
        if local_path.exists():
            return str(local_path)

        # Download
        print(f"Downloading {filename} from {model_path}...", file=sys.stderr)
        local_dir.mkdir(parents=True, exist_ok=True)
        downloaded_path = hf_hub_download(
            repo_id=model_path,
            filename=filename,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            token=token,
        )
        return downloaded_path

    except Exception as e:
        print(f"ERROR: Failed to resolve model '{model_path}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <model_path_or_repo_id>", file=sys.stderr)
        sys.exit(1)

    resolved = resolve_model(sys.argv[1])
    print(resolved)
