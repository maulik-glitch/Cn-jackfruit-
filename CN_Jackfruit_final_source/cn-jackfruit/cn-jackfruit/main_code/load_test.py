"""Concurrent client/load test; reports latency, completion and fairness."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import socket
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

MAX_MESSAGE_BYTES = 1_000_000


class TestClient:
    def __init__(self, host: str, port: int, name: str, pings: int) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.pings = pings
        self.client_id = str(uuid.uuid4())
        self.latencies: list[tuple[str, float]] = []
        self.operations = 0

    def request(self, sock: socket.socket, reader, label: str, message: dict) -> dict:
        payload = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        started = time.perf_counter()
        sock.sendall(payload)
        raw = reader.readline(MAX_MESSAGE_BYTES + 1)
        if not raw:
            raise ConnectionError("Server disconnected during a request.")
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ValueError("Server response exceeded the protocol size limit.")
        response = json.loads(raw.decode("utf-8"))
        elapsed_ms = (time.perf_counter() - started) * 1000
        self.latencies.append((label, elapsed_ms))
        self.operations += 1
        if response.get("type") == "ERROR":
            raise RuntimeError(response.get("message", "Server rejected a request."))
        return response

    def run(self) -> dict:
        started = time.perf_counter()
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as sock:
                sock.settimeout(15)
                reader = sock.makefile("rb")
                welcome = self.request(sock, reader, "HELLO", {
                    "type": "HELLO", "client_id": self.client_id, "name": self.name,
                })
                if welcome.get("type") != "WELCOME":
                    raise RuntimeError("Handshake failed.")
                exam = self.request(sock, reader, "GET_EXAM", {
                    "type": "GET_EXAM", "client_id": self.client_id,
                })
                if exam.get("type") != "EXAM":
                    raise RuntimeError("Exam delivery failed.")
                for _ in range(self.pings):
                    self.request(sock, reader, "PING", {
                        "type": "PING", "client_id": self.client_id,
                    })
                answers = {question["id"]: "A" for question in exam["questions"]}
                result = self.request(sock, reader, "SUBMIT", {
                    "type": "SUBMIT", "client_id": self.client_id, "answers": answers,
                })
                if result.get("type") != "RESULT":
                    raise RuntimeError("Submission failed.")
            return {
                "client_id": self.client_id,
                "name": self.name,
                "success": True,
                "operations": self.operations,
                "elapsed_seconds": time.perf_counter() - started,
                "score": result.get("score"),
                "status": result.get("status"),
                "latencies": self.latencies,
                "error": "",
            }
        except Exception as exc:  # Preserve per-client failures in the test report.
            return {
                "client_id": self.client_id,
                "name": self.name,
                "success": False,
                "operations": self.operations,
                "elapsed_seconds": time.perf_counter() - started,
                "score": None,
                "status": "failed",
                "latencies": self.latencies,
                "error": str(exc),
            }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def jain_fairness(values: list[float]) -> float:
    positive_values = [max(0.0, value) for value in values]
    if not positive_values or sum(value * value for value in positive_values) == 0:
        return 0.0
    return (sum(positive_values) ** 2) / (len(positive_values) * sum(value * value for value in positive_values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run concurrent exam clients against CN Jackfruit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--clients", type=int, default=25, help="Number of simultaneous student clients")
    parser.add_argument("--pings", type=int, default=2, help="Extra monitoring requests per client")
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parent / "results"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clients < 1 or args.clients > 500:
        raise SystemExit("Choose between 1 and 500 clients for this lab test.")
    if args.pings < 0 or args.pings > 100:
        raise SystemExit("PING count must be between 0 and 100.")

    overall_start = time.perf_counter()
    clients = [TestClient(args.host, args.port, f"Student-{index + 1:03d}", args.pings)
               for index in range(args.clients)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.clients) as pool:
        results = list(pool.map(lambda client: client.run(), clients))
    overall_seconds = time.perf_counter() - overall_start

    successful = [result for result in results if result["success"]]
    latencies_by_type: dict[str, list[float]] = {}
    for result in results:
        for label, latency in result["latencies"]:
            latencies_by_type.setdefault(label, []).append(latency)
    client_throughputs = [
        result["operations"] / result["elapsed_seconds"] if result["success"] and result["elapsed_seconds"] > 0 else 0.0
        for result in results
    ]
    all_latencies = [latency for values in latencies_by_type.values() for latency in values]
    operation_count = sum(result["operations"] for result in results)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host": args.host,
        "port": args.port,
        "requested_clients": args.clients,
        "successful_clients": len(successful),
        "failed_clients": args.clients - len(successful),
        "completion_rate_percent": round((len(successful) / args.clients) * 100, 2),
        "total_operations": operation_count,
        "test_duration_seconds": round(overall_seconds, 4),
        "aggregate_operations_per_second": round(operation_count / overall_seconds, 3) if overall_seconds else 0.0,
        "mean_client_throughput_ops_per_second": round(statistics.mean(client_throughputs), 3) if client_throughputs else 0.0,
        "jain_fairness_index_throughput": round(jain_fairness(client_throughputs), 4),
        "latency_ms": {
            "mean": round(statistics.mean(all_latencies), 3) if all_latencies else 0.0,
            "median": round(statistics.median(all_latencies), 3) if all_latencies else 0.0,
            "p95": round(percentile(all_latencies, 0.95), 3),
            "max": round(max(all_latencies), 3) if all_latencies else 0.0,
        },
        "latency_by_operation_ms": {
            label: {
                "count": len(values),
                "mean": round(statistics.mean(values), 3),
                "p95": round(percentile(values, 0.95), 3),
                "max": round(max(values), 3),
            }
            for label, values in sorted(latencies_by_type.items())
        },
        "clients": [
            {key: value for key, value in result.items() if key != "latencies"}
            for result in results
        ],
    }

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "load_test_latest.json"
    csv_path = output_dir / "load_test_clients_latest.csv"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "client_id", "name", "success", "operations", "elapsed_seconds", "score", "status", "error",
        ])
        writer.writeheader()
        for result in results:
            writer.writerow({key: result[key] for key in writer.fieldnames})

    print("\nCN JACKFRUIT LOAD TEST")
    print("-" * 54)
    print(f"Clients completed: {len(successful)}/{args.clients} ({summary['completion_rate_percent']}%)")
    print(f"Total operations: {operation_count}")
    print(f"Test duration: {overall_seconds:.3f} s")
    print(f"Aggregate throughput: {summary['aggregate_operations_per_second']} ops/s")
    print(f"Latency mean / median / p95: {summary['latency_ms']['mean']} / "
          f"{summary['latency_ms']['median']} / {summary['latency_ms']['p95']} ms")
    print(f"Jain throughput fairness: {summary['jain_fairness_index_throughput']:.4f} (1.0 is ideal)")
    if summary["failed_clients"]:
        print("Failures:")
        for result in results:
            if not result["success"]:
                print(f"  {result['name']}: {result['error']}")
    print(f"\nSaved report: {summary_path}")
    print(f"Saved client breakdown: {csv_path}")


if __name__ == "__main__":
    main()
