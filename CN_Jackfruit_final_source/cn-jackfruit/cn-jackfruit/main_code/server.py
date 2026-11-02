"""Concurrent TCP examination server with scoring and network telemetry."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import socket
import socketserver
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exam_data import EXAM_DURATION_SECONDS, QUESTIONS, grade_answers, public_questions

MAX_MESSAGE_BYTES = 1_000_000
METRIC_FIELDS = (
    "timestamp_utc", "client_id", "request_type", "status", "remote_ip",
    "remote_port", "request_bytes", "response_bytes", "server_processing_ms",
)
RESULT_FIELDS = (
    "timestamp_utc", "client_id", "student_name", "status", "score", "total",
    "percentage", "elapsed_seconds", "remote_ip", "remote_port",
)


class ExamService:
    """Owns exam sessions, server-side deadlines, grading, and CSV records."""

    def __init__(
        self,
        duration_seconds: int,
        log_dir: Path,
        results_file: Path | None = None,
    ) -> None:
        self.duration_seconds = duration_seconds
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._results_lock = threading.Lock()
        self._metrics_path = self.log_dir / "server_metrics.csv"
        self.results_path = Path(results_file) if results_file else self.log_dir / "exam_results.csv"
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_csv(self._metrics_path, METRIC_FIELDS)
        self._ensure_csv(self.results_path, RESULT_FIELDS)

    @staticmethod
    def _ensure_csv(path: Path, fields: tuple[str, ...]) -> None:
        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(fields)

    def record_metric(
        self,
        *,
        client_id: str,
        request_type: str,
        status: str,
        remote_address: tuple,
        request_bytes: int,
        response_bytes: int,
        processing_ms: float,
    ) -> None:
        row = [
            datetime.now(timezone.utc).isoformat(), client_id, request_type, status,
            remote_address[0], remote_address[1], request_bytes, response_bytes,
            round(processing_ms, 3),
        ]
        with self._metrics_lock:
            self._ensure_csv(self._metrics_path, METRIC_FIELDS)
            with self._metrics_path.open("a", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(row)

    def record_result(self, result: dict, remote_address: tuple) -> None:
        """Persist one accepted submission. Called only after server-side grading."""
        row = [
            datetime.now(timezone.utc).isoformat(),
            result.get("client_id", ""),
            result.get("name", "Student"),
            result.get("status", "unknown"),
            result.get("score", 0),
            result.get("total", len(QUESTIONS)),
            result.get("percentage", 0.0),
            result.get("elapsed_seconds", 0.0),
            remote_address[0],
            remote_address[1],
        ]
        with self._results_lock:
            self._ensure_csv(self.results_path, RESULT_FIELDS)
            with self.results_path.open("a", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(row)

    def handle(self, message: dict, client_id: str | None) -> tuple[dict, str]:
        request_type = str(message.get("type", "")).strip().upper()

        if request_type == "HELLO":
            if client_id is not None:
                return ({"type": "ERROR", "message": "This connection is already registered."}, "rejected")

            requested_id = str(message.get("client_id") or uuid.uuid4()).strip()
            if not requested_id or len(requested_id) > 128:
                return ({"type": "ERROR", "message": "Client ID must contain 1 to 128 characters."}, "rejected")
            name = str(message.get("name") or "Student").strip()[:80] or "Student"

            with self._lock:
                if requested_id in self._sessions:
                    return ({"type": "ERROR", "message": "This client ID is already registered. Start a new client session."}, "rejected")
                self._sessions[requested_id] = {
                    "client_id": requested_id,
                    "name": name,
                    "started_at": None,
                    "deadline": None,
                    "submitted": False,
                }
            return ({
                "type": "WELCOME",
                "client_id": requested_id,
                "message": f"Welcome, {name}. You are connected to CN Jackfruit.",
            }, "ok")

        if not client_id:
            return ({"type": "ERROR", "message": "Send HELLO before using the exam service."}, "rejected")

        with self._lock:
            session = self._sessions.get(client_id)
            if session is None:
                return ({"type": "ERROR", "message": "Unknown client. Send HELLO again."}, "rejected")

            if request_type == "PING":
                return ({
                    "type": "PONG",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                }, "ok")

            if request_type == "GET_EXAM":
                if session["submitted"]:
                    return ({"type": "ERROR", "message": "This exam has already been submitted."}, "rejected")
                if session["started_at"] is None:
                    now = time.monotonic()
                    session["started_at"] = now
                    session["deadline"] = now + self.duration_seconds
                    session["exam_id"] = str(uuid.uuid4())

                remaining = max(0, math.ceil(session["deadline"] - time.monotonic()))
                return ({
                    "type": "EXAM",
                    "exam_id": session["exam_id"],
                    "duration_seconds": self.duration_seconds,
                    "remaining_seconds": remaining,
                    "questions": public_questions(),
                }, "ok")

            if request_type == "SUBMIT":
                if session["started_at"] is None:
                    return ({"type": "ERROR", "message": "Request the exam before submitting."}, "rejected")
                if session["submitted"]:
                    return ({"type": "ERROR", "message": "A submission has already been recorded."}, "rejected")

                answers = message.get("answers", {})
                if not isinstance(answers, dict):
                    return ({"type": "ERROR", "message": "Answers must be a JSON object."}, "rejected")

                now = time.monotonic()
                elapsed = now - session["started_at"]
                expired = now >= session["deadline"]
                session["submitted"] = True

                if expired:
                    result_data = {
                        "score": 0,
                        "total": len(QUESTIONS),
                        "percentage": 0.0,
                        "correct_question_ids": [],
                        "correct_answers": {},
                    }
                    status = "time_expired"
                else:
                    result_data = grade_answers(answers)
                    status = "submitted"

                return ({
                    "type": "RESULT",
                    "client_id": client_id,
                    "status": status,
                    "expired": expired,
                    "elapsed_seconds": round(elapsed, 2),
                    "name": session["name"],
                    **result_data,
                }, status)

        return ({"type": "ERROR", "message": f"Unsupported request type: {request_type}"}, "rejected")


class ExamRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # The server must keep the connection alive while a student is answering.
        self.request.settimeout(self.server.service.duration_seconds + 60)
        client_id: str | None = None
        remote = self.client_address
        self.server.logger.info("CONNECTED | %s:%s", remote[0], remote[1])

        while True:
            try:
                raw = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
            except (ConnectionError, OSError, socket.timeout):
                break
            if not raw:
                break

            started = time.perf_counter()
            request_type = "INVALID"
            status = "error"
            response_bytes = 0
            request_client_id = client_id or ""
            oversized = len(raw) > MAX_MESSAGE_BYTES

            try:
                if oversized:
                    raise ValueError("Request exceeds the 1 MB protocol limit.")
                message = json.loads(raw.decode("utf-8"))
                if not isinstance(message, dict):
                    raise ValueError("Each message must be a JSON object.")
                request_type = str(message.get("type", "")).strip().upper()
                response, status = self.server.service.handle(message, client_id)
                if request_type == "HELLO" and response.get("type") == "WELCOME":
                    client_id = response["client_id"]
                    request_client_id = client_id
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                response = {"type": "ERROR", "message": str(exc)}
                status = "bad_request"
            except Exception:
                self.server.logger.exception("Unexpected request error")
                response = {"type": "ERROR", "message": "Internal server error."}
                status = "server_error"

            if response.get("type") == "RESULT":
                try:
                    self.server.service.record_result(response, remote)
                    self.server.logger.info(
                        "\n"
                        "==================== EXAM RESULT ====================\n"
                        "Student: %s | Client: %s\n"
                        "Marks: %s / %s | Percentage: %.2f%%\n"
                        "Status: %s | Time used: %.2f seconds\n"
                        "Saved to: %s\n"
                        "=======================================================",
                        response.get("name", "Student"),
                        response.get("client_id", ""),
                        response.get("score", 0),
                        response.get("total", len(QUESTIONS)),
                        response.get("percentage", 0.0),
                        response.get("status", "unknown"),
                        response.get("elapsed_seconds", 0.0),
                        self.server.service.results_path,
                    )
                except OSError:
                    # Never discard a student's valid result because a CSV write failed.
                    self.server.logger.exception("Could not persist the exam result CSV row.")

            payload = (json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8")
            try:
                self.wfile.write(payload)
                self.wfile.flush()
                response_bytes = len(payload)
            except (BrokenPipeError, ConnectionError, OSError):
                status = "connection_lost"
                break

            processing_ms = (time.perf_counter() - started) * 1000
            self.server.service.record_metric(
                client_id=request_client_id,
                request_type=request_type,
                status=status,
                remote_address=remote,
                request_bytes=len(raw),
                response_bytes=response_bytes,
                processing_ms=processing_ms,
            )
            self.server.logger.info(
                "%s %s client=%s status=%s service_ms=%.3f",
                remote[0], request_type, request_client_id or "-", status, processing_ms,
            )
            if oversized:
                break

        self.server.logger.info("DISCONNECTED | %s:%s", remote[0], remote[1])


class ThreadedExamServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128

    def __init__(
        self,
        address: tuple[str, int],
        service: ExamService,
        logger: logging.Logger,
        max_connections: int,
    ) -> None:
        self.service = service
        self.logger = logger
        self.max_connections = max_connections
        self._connection_slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, ExamRequestHandler)

    def process_request(self, request, client_address) -> None:
        if not self._connection_slots.acquire(blocking=False):
            self.logger.warning(
                "ADMISSION CONTROL | rejected %s:%s | connection limit=%s",
                client_address[0], client_address[1], self.max_connections,
            )
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connection_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connection_slots.release()


def build_logger(log_dir: Path) -> logging.Logger:
    logger = logging.getLogger("cn_jackfruit")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_dir / "server.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CN Jackfruit concurrent TCP exam server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: all interfaces)")
    parser.add_argument("--port", type=int, default=5050, help="TCP port (default: 5050)")
    parser.add_argument("--duration", type=int, default=EXAM_DURATION_SECONDS, help="Exam duration in seconds")
    parser.add_argument("--max-connections", type=int, default=100, help="Maximum simultaneous student connections")
    parser.add_argument("--log-dir", default=str(Path(__file__).resolve().parent / "logs"))
    parser.add_argument("--results-file", default=str(Path(__file__).resolve().parent / "results" / "exam_results.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535.")
    if not 10 <= args.duration <= 3600:
        raise SystemExit("Exam duration must be between 10 and 3600 seconds.")
    if args.max_connections < 1:
        raise SystemExit("Maximum connections must be at least 1.")

    log_dir = Path(args.log_dir).resolve()
    results_file = Path(args.results_file).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    results_file.parent.mkdir(parents=True, exist_ok=True)
    logger = build_logger(log_dir)
    service = ExamService(args.duration, log_dir, results_file)

    with ThreadedExamServer((args.host, args.port), service, logger, args.max_connections) as server:
        logger.info("=======================================================")
        logger.info("             CN JACKFRUIT EXAMINATION SERVER")
        logger.info("Listening: %s:%s", args.host, args.port)
        logger.info("Exam duration: %s seconds | Questions: %s", args.duration, len(QUESTIONS))
        logger.info("Maximum concurrent clients: %s", args.max_connections)
        logger.info("Request metrics: %s", service._metrics_path)
        logger.info("Student marks: %s", service.results_path)
        logger.info("Waiting for student clients. Press Ctrl+C to stop.")
        logger.info("=======================================================")
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            logger.info("Shutdown requested. Closing server.")


if __name__ == "__main__":
    main()
