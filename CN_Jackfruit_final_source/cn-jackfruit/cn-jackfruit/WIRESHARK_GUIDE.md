# Wireshark capture checklist

1. Start `main_code/server.py` on TCP port 5050.
2. Start a student client or `main_code/load_test.py`.
3. In Wireshark, capture on **Npcap Loopback Adapter** for a same-PC Windows demo, or on the active Wi-Fi/Ethernet interface for a second computer.
4. Apply `tcp.port == 5050` as the display filter.
5. Use **Statistics → Conversations → TCP** to inspect the client/server conversations.
6. Use **Statistics → I/O Graphs** to compare traffic during 1, 10, 25, and 50 concurrent-client runs.
7. Check retransmissions with `tcp.port == 5050 && tcp.analysis.retransmission`.
8. Export the capture as `.pcapng` and retain the matching `main_code/results/load_test_latest.json` report.

For a same-machine run, Wireshark is the packet-level view and `main_code/logs/server_metrics.csv` is the application-level view. Compare both rather than treating server processing time as network round-trip latency.

**Privacy:** this prototype uses unencrypted TCP for lab visibility. Use synthetic student names and dummy answers only.

## Optional controlled-congestion run on Kali Linux

The load test creates simultaneous application requests, but does not intentionally slow the network link. To add a repeatable impairment in a Linux lab, run `sudo tc qdisc add dev lo root netem delay 100ms 20ms loss 1%` before the same-machine localhost experiment, then remove it with `sudo tc qdisc del dev lo root`. For a two-machine setup, replace `lo` with the interface that carries the test traffic (such as `eth0` or `wlan0`). Compare baseline and impaired runs; do not apply shaping to networks you do not administer.

## SDN traffic marking (Mininet/OpenFlow lab)

When running the optional SDN lab, use this display filter to isolate exam
TCP packets marked with DSCP EF (46):

```text
tcp.port == 5050 && ip.dsfield.dscp == 46
```

Also capture the OS-Ken controller terminal and run
`ovs-ofctl -O OpenFlow13 dump-flows s1` at the Mininet prompt to show the
installed OpenFlow rules. A Windows localhost capture does not demonstrate SDN.
