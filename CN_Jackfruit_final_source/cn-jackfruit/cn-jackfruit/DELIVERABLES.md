# CN Jackfruit — deliverables and evidence checklist

The Computer Networks mini-project evaluation material describes the Jackfruit
project as having two deliverables: **SDN + Socket Programming**. This checklist
maps the repository's implementation to the two technical parts and the
supporting evidence.

## Deliverable 1 — TCP socket programming: online examination

| Requirement / behavior | Implementation | Evidence to show |
|---|---|---|
| TCP client/server communication | `main_code/server.py`, `main_code/client.py` | Wireshark TCP handshake and JSON request/response stream |
| Multiple concurrent students | Thread-per-connection TCP server with configurable admission limit | Run several clients or `load_test.py` concurrently |
| Student registration | `HELLO` / `WELCOME` exchange with per-connection client identity | Client welcome text and server connection log |
| Exam delivery | `GET_EXAM` returns public questions without answer keys | Client question screen; unit test checks answer privacy |
| Exam timer | Deadline created and enforced by the server | Take an exam and inspect `elapsed_seconds` / `time_expired` result |
| Submission and automatic grading | `SUBMIT` is graded on the server | Client result and server-side result block |
| Duplicate/invalid submission handling | Server rejects repeat submissions and malformed answer payloads | `test_server_logic.py` |
| Marks visible to examiner/server | Server logs each final score and appends a durable CSV row | `main_code/results/exam_results.csv` |
| Network monitoring | Per-request bytes, request type, status, remote endpoint, processing time | `main_code/logs/server_metrics.csv` and `server.log` |
| Scalability/performance experiment | `main_code/load_test.py` | 1 / 10 / 25 / 50-client JSON/CSV reports |

## Deliverable 2 — SDN / OpenFlow

| Requirement / behavior | Implementation | Evidence to show |
|---|---|---|
| SDN controller | `sdn/exam_controller.py` using OS-Ken | Controller terminal shows switch connection and flow classification |
| OpenFlow protocol | OpenFlow 1.3 | Switch is created with `protocols=OpenFlow13` |
| SDN-controlled topology | `sdn/exam_topology.py` using Mininet + Open vSwitch | Mininet hosts `h1`, `h2`, `h3` connected through `s1` |
| Learning / forwarding rules | Controller learns MAC locations and installs datapath flows | `ovs-ofctl -O OpenFlow13 dump-flows s1` |
| Exam traffic classification | TCP source/destination port `5050` gets DSCP EF (`46`) | `ip_dscp=46` / `set_field:46->ip_dscp` in the flow-table output |
| Socket app over SDN network | Run the same server on `h3`, clients on `h1` and `h2` | Both clients complete exams through the Mininet switch |

## Supporting evidence to capture before submission

- [ ] Server terminal showing at least two distinct student result blocks.
- [ ] `exam_results.csv` opened with the submitted names and marks.
- [ ] Unit test output ending in `OK`.
- [ ] Load-test results for 1, 10, 25, and 50 clients.
- [ ] Wireshark `.pcapng` showing TCP setup and application data on port 5050.
- [ ] OS-Ken controller log showing exam traffic classification.
- [ ] OpenFlow switch table showing the port-5050 flow and DSCP 46 action.
- [ ] Mininet topology screenshot or terminal evidence with `h1`, `h2`, `h3`, and `s1`.

**Scope honesty:** the SDN source is provided, but live SDN evidence can only be
claimed after running the Mininet/OS-Ken lab and capturing the resulting flow
table. The Windows TCP demo alone is not evidence of an OpenFlow deployment.
