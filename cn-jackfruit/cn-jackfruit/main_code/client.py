"""Interactive student client for the CN Jackfruit TCP examination service."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import uuid
from queue import Empty, Queue

MAX_MESSAGE_BYTES = 1_000_000


def send_request(sock: socket.socket, reader, message: dict) -> dict:
    payload = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
    sock.sendall(payload)
    raw = reader.readline(MAX_MESSAGE_BYTES + 1)
    if not raw:
        raise ConnectionError("Server closed the connection.")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("Server response exceeded the protocol size limit.")
    response = json.loads(raw.decode("utf-8"))
    if not isinstance(response, dict):
        raise ValueError("Server returned an invalid response.")
    return response


def timed_input(prompt: str, timeout_seconds: float) -> str | None:
    """Read terminal input without letting a blocked prompt bypass the exam timer."""
    if timeout_seconds <= 0:
        return None
    result: Queue[str] = Queue(maxsize=1)

    def read_line() -> None:
        try:
            result.put(input(prompt))
        except EOFError:
            result.put("")

    threading.Thread(target=read_line, daemon=True).start()
    try:
        return result.get(timeout=timeout_seconds)
    except Empty:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Take an exam hosted by CN Jackfruit")
    parser.add_argument("--host", default="127.0.0.1", help="Exam server IP address")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--name", default="Student", help="Student display name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_id = str(uuid.uuid4())
    try:
        with socket.create_connection((args.host, args.port), timeout=10) as sock:
            sock.settimeout(15)
            reader = sock.makefile("rb")
            welcome = send_request(sock, reader, {
                "type": "HELLO", "client_id": client_id, "name": args.name,
            })
            if welcome.get("type") != "WELCOME":
                raise RuntimeError(welcome.get("message", "Could not register with the server."))
            print(f"\n{welcome['message']}\n")

            exam = send_request(sock, reader, {"type": "GET_EXAM", "client_id": client_id})
            if exam.get("type") != "EXAM":
                raise RuntimeError(exam.get("message", "Could not load the exam."))

            duration = int(exam["duration_seconds"])
            started = time.monotonic()
            answers: dict[str, str] = {}
            print(f"Exam started. You have {duration // 60} min {duration % 60} sec.")
            print("Enter A/B/C/D for each question, or press Enter to skip.\n")
            for index, question in enumerate(exam["questions"], start=1):
                remaining = duration - (time.monotonic() - started)
                if remaining <= 0:
                    print("\nTime is up. Sending the answers already entered.")
                    break
                print(f"{index}. {question['question']}")
                for letter, option in question["options"].items():
                    print(f"   {letter}. {option}")
                print(f"   [approximately {int(remaining)} seconds remaining]")
                entered = timed_input("Your answer: ", remaining)
                if entered is None or time.monotonic() - started >= duration:
                    print("\nTime is up. Sending the answers already entered.")
                    break
                choice = entered.strip().upper()
                if choice in question["options"]:
                    answers[question["id"]] = choice
                elif choice:
                    print("Please enter A, B, C, D, or leave blank to skip.")
                print()

            result = send_request(sock, reader, {
                "type": "SUBMIT", "client_id": client_id, "answers": answers,
            })
            if result.get("type") != "RESULT":
                raise RuntimeError(result.get("message", "Submission failed."))
            print("=" * 48)
            print(f"Student: {result.get('name', args.name)}")
            print(f"Status: {result['status']}")
            print(f"Score: {result['score']} / {result['total']}")
            print(f"Percentage: {result['percentage']}%")
            print(f"Time used: {result['elapsed_seconds']} seconds")
            print("=" * 48)
            if result.get("correct_answers"):
                print("Answer key:")
                for question_id, correct in result["correct_answers"].items():
                    submitted = answers.get(question_id, "—")
                    marker = "✓" if submitted == correct else "✗"
                    print(f"  {question_id}: your answer {submitted}, correct {correct} {marker}")
    except (OSError, ConnectionError, TimeoutError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Client error: {exc}") from exc


if __name__ == "__main__":
    main()
