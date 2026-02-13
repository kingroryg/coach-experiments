#!/usr/bin/env python3
import argparse
import csv
import json
import statistics
import threading
import time
from pathlib import Path

import psutil
import requests


class MetricSampler(threading.Thread):
    def __init__(self, out_csv: Path, pid: int | None, interval_s: float = 0.5):
        super().__init__(daemon=True)
        self.out_csv = out_csv
        self.pid = pid
        self.interval_s = interval_s
        self.stop_event = threading.Event()
        self.proc = psutil.Process(pid) if pid else None

    def run(self) -> None:
        with self.out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "ts",
                    "system_cpu_pct",
                    "system_mem_pct",
                    "system_mem_used_mb",
                    "proc_cpu_pct",
                    "proc_rss_mb",
                ],
            )
            writer.writeheader()

            # Prime cpu_percent calculators
            psutil.cpu_percent(interval=None)
            if self.proc:
                self.proc.cpu_percent(interval=None)

            while not self.stop_event.is_set():
                row = {
                    "ts": time.time(),
                    "system_cpu_pct": psutil.cpu_percent(interval=None),
                    "system_mem_pct": psutil.virtual_memory().percent,
                    "system_mem_used_mb": round(psutil.virtual_memory().used / (1024 * 1024), 2),
                    "proc_cpu_pct": "",
                    "proc_rss_mb": "",
                }
                if self.proc:
                    try:
                        row["proc_cpu_pct"] = self.proc.cpu_percent(interval=None)
                        row["proc_rss_mb"] = round(
                            self.proc.memory_info().rss / (1024 * 1024), 2
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                writer.writerow(row)
                f.flush()
                time.sleep(self.interval_s)

    def stop(self) -> None:
        self.stop_event.set()


def load_prompts(path: Path) -> list[dict]:
    prompts = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                prompts.append(json.loads(line))
    return prompts


def score_response(response_text: str, spec: dict) -> dict:
    text = response_text.lower()
    expected = [k.lower() for k in spec.get("expected_keywords", [])]
    forbidden = [k.lower() for k in spec.get("forbidden_keywords", [])]

    hits = sum(1 for k in expected if k in text)
    misses = len(expected) - hits
    forbidden_hits = sum(1 for k in forbidden if k in text)

    expected_score = hits / len(expected) if expected else 1.0
    forbidden_penalty = 0.25 * forbidden_hits
    final_score = max(0.0, min(1.0, expected_score - forbidden_penalty))

    return {
        "expected_hits": hits,
        "expected_total": len(expected),
        "forbidden_hits": forbidden_hits,
        "score": round(final_score, 4),
        "misses": misses,
    }


def call_model(base_url: str, prompt: str, timeout_s: int, temperature: float, top_p: float) -> tuple[str, dict]:
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": "local-model",
        "temperature": temperature,
        "top_p": top_p,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise endpoint security assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    start = time.perf_counter()
    resp = requests.post(url, json=payload, timeout=timeout_s)
    latency_s = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    meta = {
        "latency_s": latency_s,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }
    return content, meta


def summarize(rows: list[dict], metrics_csv: Path) -> dict:
    latencies = [r["latency_s"] for r in rows if r.get("latency_s") is not None]
    scores = [r["score"] for r in rows if r.get("score") is not None]

    metrics_rows = []
    with metrics_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics_rows.append(row)

    def col_floats(key: str) -> list[float]:
        vals = []
        for r in metrics_rows:
            v = r.get(key, "")
            if v not in ("", None):
                vals.append(float(v))
        return vals

    sys_cpu = col_floats("system_cpu_pct")
    proc_cpu = col_floats("proc_cpu_pct")
    proc_rss = col_floats("proc_rss_mb")

    # Calculate percentiles
    def percentile(data: list[float], p: float) -> float | None:
        if not data:
            return None
        if len(data) < 10:
            return round(max(data), 4)
        n = int(len(data) * p / 100)
        return round(sorted(data)[n], 4)

    p50_latency = percentile(latencies, 50)
    p95_latency = percentile(latencies, 95)
    p99_latency = percentile(latencies, 99)

    p99_system_cpu = percentile(sys_cpu, 99)
    p99_proc_cpu = percentile(proc_cpu, 99)

    return {
        "prompt_count": len(rows),
        "mean_score": round(statistics.mean(scores), 4) if scores else None,
        "min_score": round(min(scores), 4) if scores else None,
        "mean_latency_s": round(statistics.mean(latencies), 4) if latencies else None,
        "p50_latency_s": p50_latency,
        "p95_latency_s": p95_latency,
        "p99_latency_s": p99_latency,
        "latency_p99_p50_ratio": round(p99_latency / p50_latency, 2) if (p99_latency and p50_latency) else None,
        "mean_system_cpu_pct": round(statistics.mean(sys_cpu), 3) if sys_cpu else None,
        "peak_system_cpu_pct": round(max(sys_cpu), 3) if sys_cpu else None,
        "p99_system_cpu_pct": p99_system_cpu,
        "mean_proc_cpu_pct": round(statistics.mean(proc_cpu), 3) if proc_cpu else None,
        "peak_proc_cpu_pct": round(max(proc_cpu), 3) if proc_cpu else None,
        "p99_proc_cpu_pct": p99_proc_cpu,
        "mean_proc_rss_mb": round(statistics.mean(proc_rss), 3) if proc_rss else None,
        "peak_proc_rss_mb": round(max(proc_rss), 3) if proc_rss else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local LLM server correctness and resource impact.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--samples-per-prompt", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--server-pid", type=int, default=None)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = load_prompts(Path(args.prompt_file))

    responses_path = out_dir / "responses.jsonl"
    metrics_path = out_dir / "metrics_samples.csv"
    summary_path = out_dir / "summary.json"

    sampler = MetricSampler(metrics_path, pid=args.server_pid, interval_s=0.5)
    sampler.start()

    rows = []
    try:
        with responses_path.open("w", encoding="utf-8") as f:
            for spec in prompts:
                for sample_idx in range(args.samples_per_prompt):
                    try:
                        response_text, meta = call_model(
                            args.base_url,
                            spec["prompt"],
                            args.timeout_s,
                            args.temperature,
                            args.top_p,
                        )
                        score = score_response(response_text, spec)

                        row = {
                            "id": spec.get("id"),
                            "category": spec.get("category"),
                            "sample_idx": sample_idx,
                            "latency_s": round(meta["latency_s"], 4),
                            "prompt_tokens": meta.get("prompt_tokens"),
                            "completion_tokens": meta.get("completion_tokens"),
                            "total_tokens": meta.get("total_tokens"),
                            "score": score["score"],
                            "expected_hits": score["expected_hits"],
                            "expected_total": score["expected_total"],
                            "forbidden_hits": score["forbidden_hits"],
                            "response": response_text,
                        }
                    except Exception as exc:
                        row = {
                            "id": spec.get("id"),
                            "category": spec.get("category"),
                            "sample_idx": sample_idx,
                            "latency_s": None,
                            "score": 0.0,
                            "error": str(exc),
                            "response": "",
                        }

                    rows.append(row)
                    f.write(json.dumps(row, ensure_ascii=True) + "\n")
                    f.flush()
    finally:
        sampler.stop()
        sampler.join(timeout=3)

    summary = summarize(rows, metrics_path)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
