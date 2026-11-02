"""Question bank and grading helpers for the CN Jackfruit lab project."""

from __future__ import annotations

QUESTIONS = [
    {
        "id": "Q1",
        "question": "Which transport-layer protocol provides reliable, ordered delivery?",
        "options": {"A": "UDP", "B": "TCP", "C": "IP", "D": "ARP"},
        "answer": "B",
    },
    {
        "id": "Q2",
        "question": "What does DNS primarily translate?",
        "options": {
            "A": "MAC addresses to port numbers",
            "B": "Domain names to IP addresses",
            "C": "IP addresses to passwords",
            "D": "Frames to electrical signals",
        },
        "answer": "B",
    },
    {
        "id": "Q3",
        "question": "Which device primarily forwards Ethernet frames using MAC addresses?",
        "options": {"A": "Hub", "B": "Router", "C": "Layer-2 switch", "D": "Modem"},
        "answer": "C",
    },
    {
        "id": "Q4",
        "question": "How many bits are in an IPv4 address?",
        "options": {"A": "16", "B": "32", "C": "64", "D": "128"},
        "answer": "B",
    },
    {
        "id": "Q5",
        "question": "Which protocol is commonly used to automatically assign IP configuration to clients?",
        "options": {"A": "DHCP", "B": "FTP", "C": "SMTP", "D": "SNMP"},
        "answer": "A",
    },
    {
        "id": "Q6",
        "question": "What is the main purpose of a subnet mask?",
        "options": {
            "A": "Encrypt application data",
            "B": "Identify the network and host portions of an IP address",
            "C": "Choose a web browser",
            "D": "Assign a TCP port",
        },
        "answer": "B",
    },
    {
        "id": "Q7",
        "question": "Which TCP mechanism helps detect lost data and support retransmission?",
        "options": {"A": "Acknowledgements and sequence numbers", "B": "DNS caching", "C": "MAC learning", "D": "NAT only"},
        "answer": "A",
    },
    {
        "id": "Q8",
        "question": "Which address is used to identify an application endpoint on a host?",
        "options": {"A": "Port number", "B": "Subnet mask", "C": "Broadcast address", "D": "SSID"},
        "answer": "A",
    },
]

EXAM_DURATION_SECONDS = 180


def public_questions() -> list[dict]:
    """Return a copy of the question bank without answer keys."""
    return [
        {
            "id": question["id"],
            "question": question["question"],
            "options": dict(question["options"]),
        }
        for question in QUESTIONS
    ]


def grade_answers(answers: dict, questions: list[dict] | None = None) -> dict:
    """Grade a mapping of question IDs to option letters."""
    bank = questions if questions is not None else QUESTIONS
    answer_key = {question["id"]: question["answer"] for question in bank}
    normalized = {
        str(question_id).upper(): str(choice).strip().upper()
        for question_id, choice in answers.items()
    }
    correct = [
        question_id
        for question_id, expected in answer_key.items()
        if normalized.get(question_id) == expected
    ]
    total = len(answer_key)
    score = len(correct)
    return {
        "score": score,
        "total": total,
        "percentage": round((score / total) * 100, 2) if total else 0.0,
        "correct_question_ids": correct,
        "correct_answers": answer_key,
    }
