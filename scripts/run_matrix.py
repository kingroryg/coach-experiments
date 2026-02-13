#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import requests
import yaml


def expand_vars(value: str) -> str:
    return os.path.expandvars(value)


def wait_for_server(base_url: str, timeout_s: int = 90) -> None:
    deadline = time.time() + timeout_s
    models_url = f"{base_url.rstrip('/')}/v1/models"

    while time.time() < deadline:
        try:
            resp = requests.get(models_url, timeout=2)
            if resp.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(f"Server did not become ready within {timeout_s}s: {base_url}")


def launch_server(env: dict, workspace: Path) -> subprocess.Popen:
    cmd = ["bash", "scripts/start_llama_server.sh"]
    proc = subprocess.Popen(
        cmd,
        cwd=workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    return proc


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_benchmark(workspace: Path, args: list[str]) -> None:
    cmd = ["python3", "scripts/benchmark.py", *args]
    subprocess.run(cmd, cwd=workspace, check=True)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark matrix by repeatedly launching llama.cpp server.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--only", default=None, help="Run only one named config")
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parent.parent
    config = load_config(Path(args.config))

    global_cfg = config["global"]
    base_url = expand_vars(global_cfg["base_url"])
    prompt_file = str((workspace / expand_vars(global_cfg["prompt_file"])).resolve())
    output_root = workspace / expand_vars(global_cfg.get("output_root", "results"))
    output_root.mkdir(parents=True, exist_ok=True)

    runs = config["runs"]
    if args.only:
        runs = [r for r in runs if r["name"] == args.only]
        if not runs:
            raise ValueError(f"No run named '{args.only}' found")

    scoreboard = []

    for run in runs:
        name = run["name"]
        print(f"\\n=== Running: {name} ===")

        env = os.environ.copy()
        env["LLAMA_SERVER_BIN"] = expand_vars(run.get("llama_server_bin", global_cfg["llama_server_bin"]))
        env["MODEL_PATH"] = expand_vars(run.get("model_path", global_cfg["model_path"]))

        for k, v in run.get("env", {}).items():
            env[k] = expand_vars(str(v))

        run_dir = output_root / name
        run_dir.mkdir(parents=True, exist_ok=True)

        server_proc = launch_server(env, workspace)
        try:
            wait_for_server(base_url, timeout_s=int(global_cfg.get("timeout_s", 90)))

            benchmark_args = [
                "--base-url",
                base_url,
                "--prompt-file",
                prompt_file,
                "--output-dir",
                str(run_dir),
                "--timeout-s",
                str(global_cfg.get("timeout_s", 90)),
                "--samples-per-prompt",
                str(global_cfg.get("samples_per_prompt", 1)),
                "--temperature",
                str(run.get("temperature", run.get("env", {}).get("TEMPERATURE", 0.0))),
                "--top-p",
                str(run.get("top_p", run.get("env", {}).get("TOP_P", 1.0))),
                "--server-pid",
                str(server_proc.pid),
            ]
            run_benchmark(workspace, benchmark_args)

            summary_path = run_dir / "summary.json"
            with summary_path.open("r", encoding="utf-8") as f:
                summary = json.load(f)

            scoreboard.append({"run": name, **summary})
        finally:
            stop_server(server_proc)
            if server_proc.stdout:
                logs = server_proc.stdout.read() or ""
                (run_dir / "server.log").write_text(logs, encoding="utf-8")

    scoreboard_path = output_root / "scoreboard.json"
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")

    print("\\n=== Scoreboard ===")
    print(json.dumps(scoreboard, indent=2))
    print(f"Wrote {scoreboard_path}")


if __name__ == "__main__":
    main()
