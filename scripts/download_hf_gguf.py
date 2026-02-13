#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GGUF model files from Hugging Face.")
    parser.add_argument("--repo-id", required=True, help="Model repo id, e.g. LiquidAI/LFM2.5-1.2B-Instruct-GGUF")
    parser.add_argument(
        "--filename",
        default=None,
        help="Exact GGUF filename to download. If omitted, all *.gguf files are pulled.",
    )
    parser.add_argument("--output-dir", default="models", help="Local output directory")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required in environment")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    allow_patterns = [args.filename] if args.filename else ["*.gguf", "*.GGUF"]
    path = snapshot_download(
        repo_id=args.repo_id,
        local_dir=out_dir / args.repo_id.replace("/", "__"),
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
        token=token,
    )
    print(path)


if __name__ == "__main__":
    main()
