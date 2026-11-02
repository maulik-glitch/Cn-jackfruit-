# CN Jackfruit — Online Examination Network

CN Jackfruit is a Computer Networks mini-project prototype for a multi-student
online examination service. It demonstrates TCP socket programming and an
optional, separate Mininet/OpenFlow SDN lab.

## Deliverables at a glance

1. **Socket programming:** threaded TCP server, multiple student clients,
   registration, exam delivery, server-enforced timing, automatic grading,
   duplicate-submission protection, server-side result display, and CSV records.
2. **SDN:** OS-Ken OpenFlow 1.3 controller plus a Mininet/Open vSwitch topology.
   The controller learns hosts, installs switch flow rules, and marks exam TCP
   traffic on port `5050` with DSCP EF (`46`).
3. **Network analysis:** request telemetry, concurrent load testing, and Wireshark
   filters/capture guidance.

See [`DELIVERABLES.md`](DELIVERABLES.md) for the feature-to-evidence checklist
and [`sdn/README.md`](sdn/README.md) for the Linux SDN demonstration.

## Project structure

```text
.
├── README.md
├── DELIVERABLES.md
├── requirements.txt
├── requirements-sdn.txt          # Optional; only for the SDN lab
├── sdn/
│   ├── exam_controller.py        # OS-Ken / OpenFlow 1.3 controller
│   ├── exam_topology.py          # Mininet topology
│   └── README.md
└── main_code/
    ├── server.py
    ├── client.py
    ├── exam_data.py
    ├── load_test.py
    ├── wireshark_filters.txt
    ├── run_server.bat
    ├── run_client.bat
    ├── run_load_test.bat
    ├── logs/                     # Created/updated at runtime
    ├── results/                  # Created/updated at runtime
    └── tests/
        ├── test_exam_logic.py
        └── test_server_logic.py
```

## Requirements

- Windows 10/11 for the ordinary TCP demo, or Linux for the TCP and SDN demos.
- Python 3.10 or newer.
- VS Code (recommended).
- Wireshark + Npcap on Windows for packet capture.
- For the **SDN deliverable only**: an Ubuntu/Mininet VM, Mininet, Open vSwitch,
  and OS-Ken. See [`sdn/README.md`](sdn/README.md).

The TCP server, client, tests, and load tester use only Python's standard
library. No `pip install` is needed for the ordinary socket demo.

## Run the TCP server and student clients in VS Code (Windows)

### 1. Get the project

In a terminal:

```powershell
git clone https://github.com/maulik-glitch/Cn-jackfruit-.git
```

In VS Code, choose **File → Open Folder** and open:

```text
Cn-jackfruit-\cn-jackfruit\cn-jackfruit
```

This is the project folder containing `main_code`, `README.md`, and `sdn`.

### 2. Check Python and run the tests

Open **Terminal → New Terminal** in VS Code:

```powershell
py --version
cd main_code
py -m unittest discover -s tests -v
```

All tests should finish with `OK`. If the `py` launcher is unavailable but
`python` works, replace `py` with `python` in the commands below.

### 3. Start the server

Keep this terminal open:

```powershell
py server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 100
```

The server terminal displays new client connections, requests, and a result
summary when each student submits. It also writes:

- `main_code/logs/server.log` — server activity and result summaries.
- `main_code/logs/server_metrics.csv` — request type, status, bytes, remote
  endpoint, and server processing time.
- `main_code/results/exam_results.csv` — one row per accepted student submission,
  including name, score, total, percentage, status, time, and remote endpoint.

### 4. Start one or more student clients

Open a **second** VS Code terminal. The server must remain running in the first:

```powershell
cd main_code
py client.py --host 127.0.0.1 --port 5050 --name "Student One"
```

Open a **third** terminal for another student:

```powershell
cd main_code
py client.py --host 127.0.0.1 --port 5050 --name "Student Two"
```

Repeat for more students. Each client has a separate TCP connection and its own
server-side exam deadline. Enter `A`, `B`, `C`, or `D` for each question. Press
Enter to leave a question unanswered. Invalid entries are re-prompted.

### 5. See the marks on the server

When a client submits, the **server terminal** prints a block similar to:

```text
==================== EXAM RESULT ====================
Student: Student One | Client: <unique-client-id>
Marks: 6 / 8 | Percentage: 75.00%
Status: submitted | Time used: 42.31 seconds
Saved to: .../main_code/results/exam_results.csv
=======================================================
```

The values above are an example; your actual marks depend on the answers
entered. Open `main_code/results/exam_results.csv` in VS Code or Excel to see
all submissions, including submissions from the load test.

For the current sample question bank, the full-mark answers are:

| Question | Correct option |
|---|---|
| Q1 | B |
| Q2 | B |
| Q3 | C |
| Q4 | B |
| Q5 | A |
| Q6 | B |
| Q7 | A |
| Q8 | A |

### 6. Stop the server

Press **Ctrl+C** in the server terminal. The server closes cleanly. Do not close
the terminal window while a student is still taking the exam.

## Run a concurrency / performance test

Keep the server running. In another terminal, from `main_code`:

```powershell
py load_test.py --host 127.0.0.1 --port 5050 --clients 1 --pings 2
py load_test.py --host 127.0.0.1 --port 5050 --clients 10 --pings 2
py load_test.py --host 127.0.0.1 --port 5050 --clients 25 --pings 2
py load_test.py --host 127.0.0.1 --port 5050 --clients 50 --pings 2
```

The load tester reports completion rate, total operations, throughput, mean /
median / p95 latency, and Jain's fairness index. It saves the latest summary to
`main_code/results/load_test_latest.json` and per-client rows to
`main_code/results/load_test_clients_latest.csv`. The test submits synthetic
answers and is intended for performance measurement, not grading real students.

## Run tests

From `main_code`:

```powershell
py -m unittest discover -s tests -v
```

## Run the SDN / OpenFlow deliverable

The SDN part is **not** enabled by the Windows localhost run. It uses a real
OpenFlow 1.3 controller connected to an Open vSwitch in Mininet. Use an Ubuntu
VM or Mininet VM, then follow every step in [`sdn/README.md`](sdn/README.md).

The key proof is the OpenFlow table output showing exam-port (`5050`) flows
with `ip_dscp` set to `46`, together with `EXAM TRAFFIC` messages in the
controller terminal. DSCP marking classifies traffic; this project does not
configure switch queues or guarantee bandwidth.

## Capture packets in Wireshark (Windows)

1. Start the server and at least one client.
2. Open Wireshark and select **Npcap Loopback Adapter** for a same-PC demo.
   For a second computer, capture on the server's Wi-Fi/Ethernet adapter.
3. Start capture and apply:

   ```text
   tcp.port == 5050
   ```

4. Submit an exam or run the load test. Inspect the TCP three-way handshake,
   data packets, connection teardown, and conversations.
5. Use **Statistics → Conversations → TCP** and **Statistics → I/O Graphs** to
   compare runs with 1, 10, 25, and 50 concurrent clients.
6. Save evidence as `.pcapng` and pair each capture with its load-test JSON and
   server metrics CSV.

See `WIRESHARK_GUIDE.md` and `main_code/wireshark_filters.txt` for additional
filters. Use synthetic names and answers only: this prototype uses unencrypted
TCP so application messages are visible in captures.

## Important limitations

- This is an academic prototype, not a production examination platform.
- Sessions are held in memory; restarting the server clears active exams.
- There is no production authentication, TLS encryption, or persistent database.
- The question bank is sample content and should be replaced with instructor-
  approved questions for an actual course assessment.
- The SDN demonstration requires Linux, Mininet, Open vSwitch, and OS-Ken. The
  controller/topology are supplied in `sdn/`, but must be run in that lab
  environment to produce live OpenFlow evidence.
