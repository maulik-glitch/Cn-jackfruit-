# CN Jackfruit — Online Examination Network

A Computer Networks mini-project prototype based on the **Online Examination Network** problem statement. It demonstrates concurrent TCP student clients, server-side exam timing, answer submission, automatic scoring, application-level traffic telemetry, and a concurrent load/fairness test.

> **Scope note:** This is a TCP client-server and traffic-monitoring prototype. It is not yet a production examination platform and does not implement a real OpenFlow/SDN controller or configure network switches. Wireshark is used to capture and inspect the packets; it does not run the Python code.

## What is implemented

- A threaded TCP server that can serve multiple student clients at the same time.
- Application-layer admission control with a configurable maximum number of simultaneous connections, so excess load is rejected instead of spawning unlimited worker threads.
- JSON messages over TCP (one JSON object per line).
- Student registration, question delivery, server-enforced exam deadline (the client automatically submits when its timed input expires), answer submission, and automatic scoring.
- Server logs with client IP/port, request type, status, byte counts, and processing time.
- A load-test program that simulates simultaneous students and reports average/median/95th-percentile response time, throughput, completion rate, and Jain's fairness index.
- A unit-test suite covering question privacy, grading, exam expiry, and duplicate submissions.
- Wireshark display filters and a capture guide.

## Requirements

- Windows 10/11 (recommended for the first demo), or Linux/Kali Linux.
- Python 3.10 or newer.
- VS Code (recommended).
- Wireshark with Npcap on Windows, or Wireshark/TShark on Linux.

No third-party Python packages are required.

## Run on Windows with VS Code

1. Download or clone this repository and open the `cn-jackfruit` folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Start the server:

   ```powershell
   cd main_code
   python server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 100
   ```

4. Open a second terminal and start one student client:

   ```powershell
   cd main_code
   python client.py --host 127.0.0.1 --port 5050 --name "Student One"
   ```

5. Open more terminals to run additional students. For a second computer on the same LAN, use the server computer's private IPv4 address instead of `127.0.0.1`. Allow Python through Windows Defender Firewall on a trusted private network when prompted.

The server writes `main_code/logs/server.log` and `main_code/logs/server_metrics.csv`.

## Run a concurrency test

Keep the server running. In another terminal:

```powershell
cd main_code
python load_test.py --host 127.0.0.1 --port 5050 --clients 25 --pings 2
```

Try 1, 10, 25, and 50 clients and compare the reports. The JSON and CSV outputs are written to `main_code/results/`.

**Metrics explained**

- **Latency:** time from sending a request until its response is received by a test client. Mean, median, p95, and maximum are reported.
- **Throughput:** completed request/response operations per second.
- **Completion rate:** percentage of simulated students that completed the handshake, exam fetch, monitoring pings, and submission.
- **Jain fairness index:** calculated over each client's completed operations per second. A value closer to 1.0 means throughput is more evenly distributed across clients.
- **Server processing time:** the server-side time spent handling each request, written to `server_metrics.csv`. It does not include the full network round trip.

## Capture packets in Wireshark on Windows

1. Install Wireshark and select the Npcap option during installation.
2. Start the Python server and at least one client.
3. Open Wireshark. For a same-PC test, choose **Npcap Loopback Adapter** if it is available. For clients on another computer, capture on the server's Wi-Fi/Ethernet adapter.
4. Start capture, then enter this display filter:

   ```text
   tcp.port == 5050
   ```

5. Submit an exam or run the load test. Stop the capture and inspect TCP conversations, packet lengths, timing, retransmissions, and connection setup/teardown.
6. For retransmission analysis, use:

   ```text
   tcp.port == 5050 && (tcp.analysis.retransmission || tcp.analysis.fast_retransmission)
   ```

The file `main_code/wireshark_filters.txt` contains these and other useful filters. Save captures as `.pcapng` if you need them for the project report. The load tester creates concurrent application traffic; it does not by itself impose bandwidth limits or packet loss. See the controlled-congestion note below for Kali Linux.

### Important Wireshark detail

The application protocol currently uses plain TCP, so the JSON exam messages are visible in packet payloads. Use only dummy/student test data. Do not use real exam credentials or personal information in this lab capture.

## Run on Kali Linux (alternative)

Install the tools:

```bash
sudo apt update
sudo apt install -y python3 wireshark tshark
```

Run the same Python commands from `main_code/`:

```bash
python3 server.py --host 0.0.0.0 --port 5050 --duration 180
python3 client.py --host 127.0.0.1 --port 5050 --name "Student One"
python3 load_test.py --host 127.0.0.1 --port 5050 --clients 25 --pings 2
```

Capture from the loopback interface for same-machine tests, or from the relevant network interface for LAN tests. Use `ip -br address` to identify interfaces and `sudo tshark -D` to list capture interfaces.

### Optional: introduce controlled network impairment on Kali

For a controlled lab experiment, `tc netem` can add delay and packet loss to the interface carrying the test traffic. On a same-machine test, try `lo`; for two machines, use the actual egress interface (for example, `eth0` or `wlan0`):

```bash
# Example only: 100 ms added delay, 20 ms variation, and 1% packet loss
sudo tc qdisc add dev lo root netem delay 100ms 20ms loss 1%

# Remove the impairment when the test is complete
sudo tc qdisc del dev lo root
```

Run the same 1/10/25/50-client load tests before and after applying impairment. Record the load-test JSON, server CSV, and matching Wireshark capture for each run. Apply traffic shaping only to your own lab interface/network. If `tc` reports that a qdisc already exists, inspect it with `sudo tc qdisc show dev lo` before changing it.

## Tests

From the `main_code` directory:

```bash
python -m unittest discover -s tests -v
```

## Repository layout

```text
cn-jackfruit/
├── README.md
├── requirements.txt
└── main_code/
    ├── server.py
    ├── client.py
    ├── exam_data.py
    ├── load_test.py
    ├── wireshark_filters.txt
    ├── run_server.bat
    ├── run_client.bat
    ├── run_load_test.bat
    ├── logs/
    ├── results/
    └── tests/
        ├── test_exam_logic.py
        └── test_server_logic.py
```

## Current limitations / next development stage

- The server stores exam sessions in memory; restarting it clears active sessions.
- The sample question bank is intentionally small and should be replaced with approved course questions.
- This prototype has no user authentication, TLS encryption, persistent database, or admin dashboard.
- The current traffic-management feature is application-layer admission control plus per-request telemetry; it is SDN-inspired, not a real SDN data plane. A later stage should add a Mininet topology and an OpenFlow controller (for example, Ryu) to install and measure switch flow rules under congestion.
